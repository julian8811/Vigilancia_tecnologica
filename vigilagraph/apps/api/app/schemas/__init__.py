"""Pydantic schemas for request/response validation."""

from __future__ import annotations

from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.schemas.search_strategy import SearchStrategyCreate, SearchStrategyUpdate, SearchStrategyResponse
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse, DocumentUploadResponse, AddUrlRequest, DocumentChunkResponse
from app.schemas.corpus import CorpusEntry, CorpusSummary
from app.schemas.graph import GraphRunResponse, GraphRunListResponse, GraphNodeResponse, GraphNodeListResponse, GraphEdgeResponse, GraphEdgeListResponse, GraphQueryRequest, GraphQueryResponse, GraphGenerateResponse
from app.schemas.analysis import TechnologyResponse, TrendResponse, ActorResponse, OpportunityResponse, AnalysisRunResponse
from app.schemas.report import ReportCreate, ReportResponse, ReportListResponse
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, ChangePasswordRequest
from app.schemas.collection_run import CollectionRunResponse, CollectionRunListResponse

__all__ = [
    "OrganizationCreate", "OrganizationUpdate", "OrganizationResponse",
    "UserCreate", "UserUpdate", "UserResponse",
    "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectListResponse",
    "SearchStrategyCreate", "SearchStrategyUpdate", "SearchStrategyResponse",
    "DocumentCreate", "DocumentUpdate", "DocumentResponse", "DocumentListResponse",
    "DocumentUploadResponse", "AddUrlRequest", "DocumentChunkResponse",
    "CorpusEntry", "CorpusSummary",
    "GraphRunResponse", "GraphRunListResponse", "GraphNodeResponse", "GraphNodeListResponse",
    "GraphEdgeResponse", "GraphEdgeListResponse", "GraphQueryRequest", "GraphQueryResponse",
    "GraphGenerateResponse",
    "TechnologyResponse", "TrendResponse", "ActorResponse", "OpportunityResponse",
    "AnalysisRunResponse",
    "ReportCreate", "ReportResponse", "ReportListResponse",
    "RegisterRequest", "LoginRequest", "TokenResponse", "ChangePasswordRequest",
    "CollectionRunResponse", "CollectionRunListResponse",
]
