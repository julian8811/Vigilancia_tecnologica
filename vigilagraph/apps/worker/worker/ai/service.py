"""AI analysis service — orchestrates LLM-powered document analysis."""

from __future__ import annotations

from structlog import get_logger
from typing import Any

from worker.ai.client import AIClient
from worker.ai.prompts import (
    SEARCH_STRATEGY_SYSTEM,
    TECHNOLOGY_EXTRACTION_SYSTEM,
    TREND_ANALYSIS_SYSTEM,
    ACTOR_EXTRACTION_SYSTEM,
    OPPORTUNITY_DETECTION_SYSTEM,
    DOCUMENT_CLASSIFICATION_SYSTEM,
    GRAPH_ENRICHMENT_SYSTEM,
)
from worker.ai.schemas import (
    SearchStrategyOutput,
    TechnologyList,
    TrendList,
    ActorList,
    OpportunityList,
    GraphEnrichment,
)

logger = get_logger(__name__)


class AnalysisService:
    """Orchestrates AI analysis using LLM calls.

    Every public method accepts relevant context and returns a structured
    Pydantic model.  API keys are loaded from ``app.core.config`` when
    available; fall back to env vars.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model = model
        self._client: AIClient | None = None

    # ── Client lazy-init ──────────────────────────────────────

    def _get_client(self) -> AIClient:
        if self._client is None:
            key = self._api_key
            if not key:
                from app.core.config import settings
                key = settings.OPENAI_API_KEY
            self._client = AIClient(api_key=key, model=self._model)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()

    # ── Search Strategy ───────────────────────────────────────

    async def generate_search_strategy(
        self,
        topic: str,
        *,
        objective: str | None = None,
        country: str | None = None,
        language: str = "es",
    ) -> SearchStrategyOutput:
        """Generate a multi-lingual search strategy from a topic."""
        user = (
            f"Tema: {topic}\n"
            f"Objetivo: {objective or 'No especificado'}\n"
            f"País: {country or 'No especificado'}\n"
            f"Idioma: {language}\n"
        )
        result = await self._get_client().structured(
            system=SEARCH_STRATEGY_SYSTEM,
            user=user,
            response_model=SearchStrategyOutput,
        )
        logger.info("ai_search_strategy_generated", topic=topic[:80])
        return result

    # ── Document Analysis ─────────────────────────────────────

    async def extract_technologies(self, title: str, abstract: str) -> TechnologyList:
        """Extract technologies, methods, and applications from a document."""
        user = f"Título: {title}\n\nResumen:\n{abstract[:4000]}"
        result = await self._get_client().structured(
            system=TECHNOLOGY_EXTRACTION_SYSTEM,
            user=user,
            response_model=TechnologyList,
        )
        logger.info("ai_technologies_extracted", title=title[:80], count=len(result.technologies))
        return result

    async def analyze_trends(self, corpus_summary: str) -> TrendList:
        """Analyze trends from a corpus summary or document set."""
        user = f"Corpus de documentos:\n\n{corpus_summary[:8000]}"
        result = await self._get_client().structured(
            system=TREND_ANALYSIS_SYSTEM,
            user=user,
            response_model=TrendList,
        )
        logger.info("ai_trends_analyzed", count=len(result.trends))
        return result

    async def extract_actors(self, corpus_text: str) -> ActorList:
        """Extract key actors from corpus content."""
        user = f"Contenido del corpus:\n\n{corpus_text[:8000]}"
        result = await self._get_client().structured(
            system=ACTOR_EXTRACTION_SYSTEM,
            user=user,
            response_model=ActorList,
        )
        logger.info("ai_actors_extracted", count=len(result.actors))
        return result

    async def detect_opportunities(self, analysis_context: str) -> OpportunityList:
        """Detect opportunities from analysis context."""
        user = f"Contexto de análisis:\n\n{analysis_context[:8000]}"
        result = await self._get_client().structured(
            system=OPPORTUNITY_DETECTION_SYSTEM,
            user=user,
            response_model=OpportunityList,
        )
        logger.info("ai_opportunities_detected", count=len(result.opportunities))
        return result

    # ── Graph Enrichment ──────────────────────────────────────

    async def enrich_node(
        self,
        label: str,
        node_type: str | None,
        context: str = "",
    ) -> GraphEnrichment:
        """Enrich a single graph node with AI metadata."""
        user = (
            f"Nodo: {label}\n"
            f"Tipo actual: {node_type or 'desconocido'}\n"
            f"Contexto: {context[:2000]}"
        )
        result = await self._get_client().structured(
            system=GRAPH_ENRICHMENT_SYSTEM,
            user=user,
            response_model=GraphEnrichment,
        )
        return result

    # ── Bulk Analysis Pipeline ────────────────────────────────

    async def analyze_project(
        self,
        *,
        topic: str,
        corpus_text: str,
        docs_summary: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Run the full analysis pipeline for a project.

        Returns a dict with technologies, trends, actors, and opportunities.
        Each key contains the raw Pydantic model (caller serializes).
        """
        # Run analyses in parallel
        import asyncio

        doc_text = "\n".join(
            f"- {d.get('title', '?')}: {d.get('abstract', '')[:300]}"
            for d in (docs_summary or [])
        )

        tech_task = self.extract_technologies(topic, corpus_text[:4000])
        trends_task = self.analyze_trends(doc_text[:8000])
        actors_task = self.extract_actors(doc_text[:8000])
        opps_task = self.detect_opportunities(
            f"Tema: {topic}\n\nDocumentos:\n{doc_text[:6000]}"
        )

        technologies, trends, actors, opportunities = await asyncio.gather(
            tech_task, trends_task, actors_task, opps_task,
        )

        logger.info(
            "ai_analysis_pipeline_complete",
            technologies=len(technologies.technologies),
            trends=len(trends.trends),
            actors=len(actors.actors),
            opportunities=len(opportunities.opportunities),
        )

        return {
            "technologies": technologies,
            "trends": trends,
            "actors": actors,
            "opportunities": opportunities,
        }
