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
from app.core.graph_types import NODE_TYPE_MAP, EDGE_TYPE_MAP
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
        """Trigger graph generation for a project (synchronous subprocess)."""
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # 1. Get documents directly from DB
        from app.models.document import Document
        from sqlalchemy import select
        docs_result = await self.db.execute(
            select(Document).where(Document.project_id == project_id).limit(200)
        )
        docs = docs_result.scalars().all()

        if not docs:
            raise HTTPException(status_code=400, detail="No hay documentos disponibles")

        # 2. Create flat corpus directory with .md files
        flat_corpus = Path(settings.STORAGE_LOCAL_PATH) / "flat_corpus" / str(project_id)
        if flat_corpus.exists():
            shutil.rmtree(flat_corpus)
        flat_corpus.mkdir(parents=True, exist_ok=True)

        for doc in docs:
            if not doc.abstract:
                continue
            fname = flat_corpus / f"{doc.id}.md"
            content = f"# {doc.title or 'Sin título'}\n\n"
            if doc.authors:
                try:
                    authors = json.loads(doc.authors) if isinstance(doc.authors, str) else doc.authors
                    content += f"**Authors:** {', '.join(str(a) for a in (authors if isinstance(authors, list) else [authors]))}\n\n"
                except (json.JSONDecodeError, TypeError):
                    content += f"**Authors:** {doc.authors}\n\n"
            if doc.publication_year:
                content += f"**Year:** {doc.publication_year}\n\n"
            content += doc.abstract
            fname.write_text(content, encoding='utf-8')

        doc_count = len(list(flat_corpus.glob("*.md")))
        if doc_count == 0:
            raise HTTPException(status_code=400, detail="No hay documentos con resúmenes disponibles")

        # 3. Create GraphRun record
        run = GraphRun(
            project_id=project_id,
            status="running",
            started_at=datetime.now(UTC),
            input_corpus_path=str(flat_corpus),
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)

        run_id = run.id
        # Graphify puts output in graphify-out/ inside the input directory
        graphify_out = Path(str(flat_corpus)) / "graphify-out"
        output_dir = str(graphify_out)

        try:
            # 4. Run Graphify CLI on the flat corpus
            command = settings.GRAPHIFY_COMMAND
            cmd = [
                command,
                str(flat_corpus),
            ]

            logger.info(
                "graphify_subprocess_start",
                run_id=run_id,
                command=command,
                corpus_path=str(flat_corpus),
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
                run.error_message = "El subproceso de Graphify excedió el tiempo límite de 3600 segundos"
                run.finished_at = datetime.now(UTC)
                await self.db.flush()
                logger.error("graphify_timeout", run_id=run_id)
                return GraphGenerateResponse(
                    message="La generación del grafo excedió el tiempo límite",
                    run_id=run_id,
                    status="failed",
                )

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace") if stderr else "Unknown error"
                run.status = "failed"
                run.error_message = f"Graphify terminó con código {proc.returncode}: {error_msg[:2000]}"
                run.finished_at = datetime.now(UTC)
                await self.db.flush()
                logger.error("graphify_failed", run_id=run_id, returncode=proc.returncode)
                return GraphGenerateResponse(
                    message="Falló la generación del grafo",
                    run_id=run_id,
                    status="failed",
                )

            # 5. Locate graph.json (Graphify puts it in graphify-out/ inside input dir)
            graph_json_path = graphify_out / "graph.json"
            if not graph_json_path.exists():
                run.status = "failed"
                run.error_message = "Graphify finalizó pero no se encontró graph.json en la salida"
                run.finished_at = datetime.now(UTC)
                await self.db.flush()
                return GraphGenerateResponse(
                    message="Falló la generación del grafo: no se encontró la salida",
                    run_id=run_id,
                    status="failed",
                )

            graph_data = json.loads(graph_json_path.read_text())

            # Handle both "edges" and "links" (Graphify uses "links")
            if "links" in graph_data and "edges" not in graph_data:
                graph_data["edges"] = graph_data.pop("links")

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
                message="Grafo generado exitosamente",
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
                message=f"Falló la generación del grafo: {exc}",
                run_id=run_id,
                status="failed",
            )

    async def get_latest(self, project_id: uuid.UUID, org_id: uuid.UUID) -> GraphRunResponse | None:
        """Return the most recent completed graph run for a project."""
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

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
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

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
            node_id = str(node_data.get("id", str(uuid.uuid4()))).replace(".", "_")
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
                str(edge_data.get("type", edge_data.get("relation", "related_to"))).lower(),
                str(edge_data.get("type", edge_data.get("relation", "related_to"))),
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

    async def get_run(self, run_id: uuid.UUID) -> GraphRun:
        """Fetch a graph run by ID (no org check — caller must verify)."""
        run = await self.run_repo.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución de grafo no encontrada")
        return run

    async def _get_run_with_org_check(self, run_id: uuid.UUID, org_id: uuid.UUID) -> GraphRun:
        """Verify a graph run belongs to the user's org via its project."""
        run = await self.run_repo.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ejecución de grafo no encontrada")

        project = await self.project_repo.get_with_org_check(run.project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Ejecución de grafo no encontrada")

        return run
