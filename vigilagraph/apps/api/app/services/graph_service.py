"""Graph service — orchestrates Graphify subprocess runs for knowledge-graph generation."""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import datetime, UTC
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.models.graph import GraphEdge, GraphNode, GraphRun
from app.repositories.graph_repository import GraphEdgeRepository, GraphNodeRepository, GraphRunRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.graph import (
    GraphEdgeListResponse,
    GraphEdgeResponse,
    GraphGenerateResponse,
    GraphNodeListResponse,
    GraphNodeResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphRunListResponse,
    GraphRunResponse,
)
from app.services.corpus_service import CorpusService

logger = get_logger(__name__)

# Type maps for Graphify graph.json → internal representation
NODE_TYPE_MAP: dict[str, str] = {
    "technology": "technology",
    "paper": "paper",
    "author": "author",
    "institution": "institution",
    "concept": "concept",
    "topic": "topic",
    "method": "method",
    "application": "application",
    "material": "material",
    "organization": "organization",
    "person": "person",
    "location": "location",
    "event": "event",
    "product": "product",
    "dataset": "dataset",
    "tool": "tool",
    "field": "field",
    "subfield": "subfield",
}

EDGE_TYPE_MAP: dict[str, str] = {
    "related_to": "related_to",
    "cites": "cites",
    "authored_by": "authored_by",
    "developed_by": "developed_by",
    "uses_method": "uses_method",
    "mentions": "mentions",
    "part_of": "part_of",
    "application_of": "application_of",
    "improves": "improves",
    "precedes": "precedes",
    "collaborates_with": "collaborates_with",
    "funded_by": "funded_by",
}


class GraphService:
    """Orchestrates knowledge-graph generation via the Graphify CLI.

    Flow:
      1. Rebuild corpus (text files for Graphify input)
      2. Run Graphify CLI as subprocess
      3. Parse graph.json output
      4. Import nodes and edges into DB
      5. Mark run as completed
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.run_repo = GraphRunRepository(db)
        self.node_repo = GraphNodeRepository(db)
        self.edge_repo = GraphEdgeRepository(db)
        self.project_repo = ProjectRepository(db)
        self.corpus_service = CorpusService(db)

    async def generate(self, project_id: uuid.UUID, org_id: uuid.UUID) -> GraphGenerateResponse:
        """Trigger graph generation for a project.

        MVP: runs synchronously (blocking subprocess). Production will
        delegate to a Celery task with a polling endpoint.
        """
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # 1. Rebuild corpus
        corpus_ready = await self.corpus_service.ready(project_id, org_id)
        if not corpus_ready:
            # Auto-rebuild if corpus doesn't exist yet
            await self.corpus_service.rebuild(project_id, org_id)

        corpus_summary = await self.corpus_service.summary(project_id, org_id)
        if not corpus_summary.corpus_ready:
            raise HTTPException(
                status_code=400,
                detail="No extracted documents available. Upload and extract documents first.",
            )

        corpus_path = corpus_summary.corpus_path
        if corpus_path is None:
            raise HTTPException(status_code=400, detail="Corpus path not available")

        # 2. Create GraphRun record
        run = GraphRun(
            project_id=project_id,
            status="running",
            started_at=datetime.now(UTC),
            input_corpus_path=corpus_path,
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)

        run_id = run.id
        output_dir = str(Path(settings.STORAGE_LOCAL_PATH) / "graphify_output" / str(run_id))
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        try:
            # 3. Run Graphify CLI via subprocess
            command = settings.GRAPHIFY_COMMAND
            cmd = [
                command,
                corpus_path,
                "--output-dir", output_dir,
                "--format", "json",
            ]

            logger.info(
                "graphify_subprocess_start",
                run_id=run_id,
                command=command,
                corpus_path=corpus_path,
            )

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=3600,  # 1 hour timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                run.status = "failed"
                run.error_message = "Graphify subprocess timed out after 3600 seconds"
                run.finished_at = datetime.now(UTC)
                await self.db.flush()
                logger.error("graphify_timeout", run_id=run_id)
                return GraphGenerateResponse(
                    message="Graph generation timed out",
                    run_id=run_id,
                    status="failed",
                )

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace") if stderr else "Unknown error"
                run.status = "failed"
                run.error_message = f"Graphify exited with code {proc.returncode}: {error_msg[:2000]}"
                run.finished_at = datetime.now(UTC)
                await self.db.flush()
                logger.error("graphify_failed", run_id=run_id, returncode=proc.returncode)
                return GraphGenerateResponse(
                    message="Graph generation failed",
                    run_id=run_id,
                    status="failed",
                )

            # 4. Parse graph.json
            graph_json_path = Path(output_dir) / "graph.json"
            if not graph_json_path.exists():
                run.status = "failed"
                run.error_message = "Graphify completed but graph.json not found in output"
                run.finished_at = datetime.now(UTC)
                await self.db.flush()
                return GraphGenerateResponse(
                    message="Graph generation failed: output not found",
                    run_id=run_id,
                    status="failed",
                )

            graph_data = json.loads(graph_json_path.read_text())

            # 5. Import nodes and edges
            nodes_imported = await self._import_nodes(run_id, graph_data)
            edges_imported = await self._import_edges(run_id, graph_data, graph_data.get("nodes", []))

            # 6. Update run stats
            run.status = "completed"
            run.finished_at = datetime.now(UTC)
            run.node_count = nodes_imported
            run.edge_count = edges_imported
            run.community_count = graph_data.get("community_count", 0)
            run.graph_json_path = str(graph_json_path)
            run.graphify_version = "graphify"

            # Check for HTML output
            html_path = Path(output_dir) / "graph.html"
            if html_path.exists():
                run.graph_html_path = str(html_path)

            report_path = Path(output_dir) / "report.json"
            if report_path.exists():
                run.graph_report_path = str(report_path)

            run.stats = {
                "nodes_imported": nodes_imported,
                "edges_imported": edges_imported,
                "community_count": run.community_count,
            }
            run.output_path = output_dir

            await self.db.flush()

            logger.info(
                "graphify_completed",
                run_id=run_id,
                nodes=nodes_imported,
                edges=edges_imported,
                communities=run.community_count,
            )

            return GraphGenerateResponse(
                message="Graph generated successfully",
                run_id=run_id,
                status="completed",
            )

        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)[:2000]
            run.finished_at = datetime.now(UTC)
            await self.db.flush()
            logger.exception("graphify_exception", run_id=run_id)
            return GraphGenerateResponse(
                message=f"Graph generation failed: {exc}",
                run_id=run_id,
                status="failed",
            )

    async def get_latest(self, project_id: uuid.UUID, org_id: uuid.UUID) -> GraphRunResponse | None:
        """Return the most recent completed graph run for a project."""
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        run = await self.run_repo.get_latest_by_project(project_id)
        if run is None:
            return None
        return GraphRunResponse.model_validate(run)

    async def list_runs(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> GraphRunListResponse:
        """Paginated list of graph runs for a project."""
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        items, total = await self.run_repo.list_by_project(project_id, page=page, page_size=page_size)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return GraphRunListResponse(
            items=[GraphRunResponse.model_validate(r) for r in items],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    async def list_nodes(
        self,
        run_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        node_type: str | None = None,
        search: str | None = None,
        min_centrality: float | None = None,
        community_id: int | None = None,
    ) -> GraphNodeListResponse:
        """Paginated list of graph nodes with filters."""
        run = await self._get_run_with_org_check(run_id, org_id)
        items, total = await self.node_repo.list_by_run(
            run_id,
            page=page,
            page_size=page_size,
            node_type=node_type,
            search=search,
            min_centrality=min_centrality,
            community_id=community_id,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return GraphNodeListResponse(
            items=[GraphNodeResponse.model_validate(n) for n in items],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    async def list_edges(
        self,
        run_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        edge_type: str | None = None,
    ) -> GraphEdgeListResponse:
        """Paginated list of graph edges."""
        run = await self._get_run_with_org_check(run_id, org_id)
        items, total = await self.edge_repo.list_by_run(
            run_id, page=page, page_size=page_size, edge_type=edge_type,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return GraphEdgeListResponse(
            items=[GraphEdgeResponse.model_validate(e) for e in items],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    async def query_graph(
        self,
        run_id: uuid.UUID,
        org_id: uuid.UUID,
        query: GraphQueryRequest,
    ) -> GraphQueryResponse:
        """Query the knowledge graph with filters."""
        run = await self._get_run_with_org_check(run_id, org_id)

        nodes, total_nodes = await self.node_repo.list_by_run(
            run_id,
            page=1,
            page_size=query.limit or 50,
            node_type=query.node_types[0] if query.node_types else None,
            search=query.search,
            min_centrality=query.min_centrality,
            community_id=query.community_id,
        )

        edges, total_edges = await self.edge_repo.list_by_run(
            run_id,
            page=1,
            page_size=query.limit or 50,
        )

        return GraphQueryResponse(
            nodes=[GraphNodeResponse.model_validate(n) for n in nodes],
            edges=[GraphEdgeResponse.model_validate(e) for e in edges],
            total_nodes=total_nodes,
            total_edges=total_edges,
        )

    async def find_path(
        self,
        run_id: uuid.UUID,
        org_id: uuid.UUID,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        max_depth: int = 5,
    ) -> list[GraphEdgeResponse]:
        """BFS path finding between two nodes."""
        run = await self._get_run_with_org_check(run_id, org_id)
        edges = await self.edge_repo.find_path(source_node_id, target_node_id, run_id, max_depth)
        return [GraphEdgeResponse.model_validate(e) for e in edges]

    # ── Internal helpers ──────────────────────────────────────────

    async def _import_nodes(self, run_id: uuid.UUID, graph_data: dict) -> int:
        """Import nodes from parsed graph.json into the database."""
        nodes_raw = graph_data.get("nodes", [])
        if not nodes_raw:
            return 0

        imported = 0
        for node_data in nodes_raw:
            node_id = node_data.get("id", str(uuid.uuid4()))
            label = node_data.get("label", node_data.get("name", "unknown"))
            node_type = NODE_TYPE_MAP.get(
                node_data.get("type", "").lower(),
                node_data.get("type", "concept"),
            )
            community = node_data.get("community", node_data.get("community_id"))
            centrality = node_data.get("centrality", node_data.get("centrality_score"))

            metadata = {}
            for key in ("description", "url", "source", "aliases", "mentions", "properties"):
                if key in node_data:
                    metadata[key] = node_data[key]

            node = GraphNode(
                run_id=run_id,
                external_node_id=str(node_id),
                label=str(label)[:500],
                node_type=str(node_type)[:50] if node_type else None,
                community_id=int(community) if community is not None else None,
                centrality_score=float(centrality) if centrality is not None else None,
                metadata_json=metadata or None,
            )
            self.db.add(node)
            imported += 1

        await self.db.flush()
        return imported

    async def _import_edges(self, run_id: uuid.UUID, graph_data: dict, nodes: list[dict]) -> int:
        """Import edges from parsed graph.json into the database."""
        edges_raw = graph_data.get("edges", [])
        if not edges_raw:
            return 0

        # Build external_node_id → DB id mapping for edges in this run
        from sqlalchemy import select
        existing_nodes = await self.db.execute(
            select(GraphNode).where(GraphNode.run_id == run_id)
        )
        node_map: dict[str, uuid.UUID] = {}
        for node in existing_nodes.scalars().unique().all():
            node_map[node.external_node_id] = node.id

        imported = 0
        for edge_data in edges_raw:
            source_ext = str(edge_data.get("source", ""))
            target_ext = str(edge_data.get("target", ""))

            source_id = node_map.get(source_ext)
            target_id = node_map.get(target_ext)

            if source_id is None or target_id is None:
                continue

            edge_type = EDGE_TYPE_MAP.get(
                edge_data.get("type", "").lower(),
                edge_data.get("type", "related_to"),
            )
            weight = edge_data.get("weight", edge_data.get("strength"))

            metadata = {}
            for key in ("label", "properties", "source", "evidence"):
                if key in edge_data:
                    metadata[key] = edge_data[key]

            edge = GraphEdge(
                run_id=run_id,
                source_node_id=source_id,
                target_node_id=target_id,
                edge_type=str(edge_type)[:50] if edge_type else None,
                weight=float(weight) if weight is not None else None,
                metadata_json=metadata or None,
            )
            self.db.add(edge)
            imported += 1

        await self.db.flush()
        return imported

    async def _get_run_with_org_check(self, run_id: uuid.UUID, org_id: uuid.UUID) -> GraphRun:
        """Verify a graph run belongs to the user's org via its project."""
        run = await self.run_repo.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Graph run not found")

        project = await self.project_repo.get_with_org_check(run.project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Graph run not found")

        return run
