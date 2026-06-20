"""Graph DB importer for the Celery worker path.

ParsedGraph → GraphNode / GraphEdge bulk insert via SQLAlchemy.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from worker.graphify.parser import ParsedGraph, ParsedNode, ParsedEdge

logger = logging.getLogger(__name__)


class GraphDBImporter:
    """Import a ``ParsedGraph`` into the database for a given run.

    This is used by the Celery worker path (not the API's inline path).
    It maps external IDs to internal DB IDs and bulk-inserts nodes then
    edges.
    """

    def __init__(self, db: AsyncSession, run_id: Any) -> None:
        self.db = db
        self.run_id = run_id
        self._node_id_map: dict[str, Any] = {}

    async def import_graph(self, graph: ParsedGraph) -> dict[str, int]:
        """Import the full parsed graph into the database.

        Returns a dict with ``nodes_inserted`` and ``edges_inserted`` counts.
        """
        node_count = await self._import_nodes(graph.nodes)
        edge_count = await self._import_edges(graph.edges)

        logger.info(
            "Graph import complete",
            run_id=str(self.run_id),
            nodes=node_count,
            edges=edge_count,
            communities=graph.community_count,
        )

        return {
            "nodes_inserted": node_count,
            "edges_inserted": edge_count,
        }

    async def _import_nodes(self, nodes: list[ParsedNode]) -> int:
        """Insert nodes and build the external-ID → DB-ID mapping."""
        from app.models.graph import GraphNode

        count = 0
        for parsed in nodes:
            node = GraphNode(
                run_id=self.run_id,
                external_node_id=parsed.external_id,
                label=parsed.label,
                node_type=parsed.node_type,
                community_id=parsed.community_id,
                centrality_score=parsed.centrality_score,
                metadata_json=parsed.metadata or None,
            )
            self.db.add(node)
            count += 1

        await self.db.flush()

        # Build mapping by querying back external_node_ids for this run
        result = await self.db.execute(
            select(GraphNode).where(GraphNode.run_id == self.run_id),
        )
        for node in result.scalars().unique().all():
            self._node_id_map[node.external_node_id] = node.id

        return count

    async def _import_edges(self, edges: list[ParsedEdge]) -> int:
        """Insert edges using the node ID map."""
        from app.models.graph import GraphEdge

        count = 0
        for parsed in edges:
            source_id = self._node_id_map.get(parsed.source_external_id)
            target_id = self._node_id_map.get(parsed.target_external_id)

            if source_id is None or target_id is None:
                logger.warning(
                    "Skipping edge with unresolvable node IDs",
                    source=parsed.source_external_id,
                    target=parsed.target_external_id,
                )
                continue

            edge = GraphEdge(
                run_id=self.run_id,
                source_node_id=source_id,
                target_node_id=target_id,
                edge_type=parsed.edge_type,
                weight=parsed.weight,
                metadata_json=parsed.metadata or None,
            )
            self.db.add(edge)
            count += 1

        await self.db.flush()
        return count
