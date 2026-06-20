"""Graph repositories — GraphRun, GraphNode, GraphEdge data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.graph import GraphEdge, GraphNode, GraphRun
from app.repositories.base import BaseRepository


class GraphRunRepository(BaseRepository[GraphRun]):
    """Repository for ``GraphRun`` CRUD with project-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GraphRun, session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[GraphRun], int]:
        """Return paginated graph runs for a project."""
        base = select(GraphRun).where(GraphRun.project_id == project_id)

        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = base.order_by(GraphRun.created_at.desc()).offset(offset).limit(page_size)
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().unique().all())

        return items, total

    async def get_latest_by_project(self, project_id: uuid.UUID) -> GraphRun | None:
        """Return the most recent completed graph run for a project."""
        stmt = (
            select(GraphRun)
            .where(GraphRun.project_id == project_id)
            .order_by(GraphRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class GraphNodeRepository(BaseRepository[GraphNode]):
    """Repository for ``GraphNode`` CRUD with run-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GraphNode, session)

    async def list_by_run(
        self,
        run_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        node_type: str | None = None,
        search: str | None = None,
        min_centrality: float | None = None,
        community_id: int | None = None,
    ) -> tuple[list[GraphNode], int]:
        """Return paginated nodes for a run, with optional filters."""
        base = select(GraphNode).where(GraphNode.run_id == run_id)

        if node_type:
            base = base.where(GraphNode.node_type == node_type)
        if search:
            base = base.where(GraphNode.label.ilike(f"%{search}%"))
        if min_centrality is not None:
            base = base.where(GraphNode.centrality_score >= min_centrality)
        if community_id is not None:
            base = base.where(GraphNode.community_id == community_id)

        # Total count
        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar_one()

        # Paginated items
        offset = (page - 1) * page_size
        stmt = base.order_by(GraphNode.centrality_score.desc().nullslast()).offset(offset).limit(page_size)
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().unique().all())

        return items, total

    async def get_by_external_id(self, run_id: uuid.UUID, external_node_id: str) -> GraphNode | None:
        """Find a node by its external (Graphify) ID within a run."""
        stmt = (
            select(GraphNode)
            .where(GraphNode.run_id == run_id)
            .where(GraphNode.external_node_id == external_node_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class GraphEdgeRepository(BaseRepository[GraphEdge]):
    """Repository for ``GraphEdge`` CRUD with run-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GraphEdge, session)

    async def list_by_run(
        self,
        run_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        edge_type: str | None = None,
    ) -> tuple[list[GraphEdge], int]:
        """Return paginated edges for a run."""
        base = select(GraphEdge).where(GraphEdge.run_id == run_id)
        if edge_type:
            base = base.where(GraphEdge.edge_type == edge_type)

        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = base.order_by(GraphEdge.weight.desc().nullslast()).offset(offset).limit(page_size)
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().unique().all())

        return items, total

    async def neighbors(self, node_id: uuid.UUID, run_id: uuid.UUID) -> list[GraphEdge]:
        """Return all edges connected to *node_id* within a run."""
        stmt = (
            select(GraphEdge)
            .where(GraphEdge.run_id == run_id)
            .where(
                (GraphEdge.source_node_id == node_id) | (GraphEdge.target_node_id == node_id),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def find_path(
        self,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        run_id: uuid.UUID,
        max_depth: int = 5,
    ) -> list[GraphEdge]:
        """BFS-based path finding between two nodes in a run.

        Returns the list of edges forming the path, or an empty list if
        no path is found within *max_depth*.
        """
        from collections import deque

        # Build adjacency list for the run
        stmt = select(GraphEdge).where(GraphEdge.run_id == run_id)
        result = await self.session.execute(stmt)
        all_edges = list(result.scalars().unique().all())

        graph: dict[uuid.UUID, list[tuple[uuid.UUID, GraphEdge]]] = {}
        for edge in all_edges:
            graph.setdefault(edge.source_node_id, []).append((edge.target_node_id, edge))
            graph.setdefault(edge.target_node_id, []).append((edge.source_node_id, edge))

        # BFS
        visited: set[uuid.UUID] = {source_node_id}
        queue: deque[tuple[uuid.UUID, list[GraphEdge]]] = deque([(source_node_id, [])])

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            for neighbor, edge in graph.get(current, []):
                if neighbor == target_node_id:
                    return path + [edge]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [edge]))

        return []
