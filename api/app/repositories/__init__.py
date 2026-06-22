"""Repository layer — data access for all VigilaGraph entities."""

from __future__ import annotations

from app.repositories.analysis_repository import (
    ActorRepository,
    OpportunityRepository,
    TechnologyRepository,
    TrendRepository,
)
from app.repositories.base import BaseRepository
from app.repositories.collection_run_repository import CollectionRunRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.graph_repository import GraphEdgeRepository, GraphNodeRepository, GraphRunRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.search_strategy_repository import SearchStrategyRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ProjectRepository",
    "SearchStrategyRepository",
    "DocumentRepository",
    "OrganizationRepository",
    "CollectionRunRepository",
    "GraphRunRepository",
    "GraphNodeRepository",
    "GraphEdgeRepository",
    "TechnologyRepository",
    "TrendRepository",
    "ActorRepository",
    "OpportunityRepository",
    "ReportRepository",
]
