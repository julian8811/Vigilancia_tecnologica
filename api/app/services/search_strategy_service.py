"""Search-strategy service — keyword configuration with AI-powered generation."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.search_strategy import SearchStrategy
from app.repositories.project_repository import ProjectRepository
from app.repositories.search_strategy_repository import SearchStrategyRepository
from app.schemas.search_strategy import SearchStrategyCreate, SearchStrategyResponse, SearchStrategyUpdate
from app.services.ai_service import generate_search_strategy as ai_generate

logger = get_logger(__name__)

_SYNONYM_MAP: dict[str, list[str]] = {
    "ia": ["inteligencia artificial", "machine learning", "aprendizaje automático", "deep learning"],
    "machine": ["learning", "deep learning"],
    "learning": ["machine", "deep learning"],
    "seguridad": ["ciberseguridad", "seguridad informática", "security", "cybersecurity"],
    "cloud": ["nube", "computación en la nube"],
    "data": ["datos", "big data", "analítica", "analysis"],
    "iot": ["internet de las cosas", "internet of things"],
    "blockchain": ["cadena de bloques", "distributed ledger"],
    "hardware": ["dispositivo", "equipo"],
    "software": ["programa", "aplicación", "app"],
    "red": ["network", "networking"],
    "nube": ["cloud", "computación en la nube"],
    "ciberseguridad": ["seguridad informática", "security", "cybersecurity"],
}


class SearchStrategyService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SearchStrategyRepository(db)
        self.project_repo = ProjectRepository(db)

    async def get_strategy(self, project_id: uuid.UUID, org_id: uuid.UUID) -> SearchStrategyResponse | None:
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        strategy = await self.repo.get_by_project(project_id)
        if strategy is None:
            return None
        return SearchStrategyResponse.model_validate(strategy)

    async def update_strategy(
        self, project_id: uuid.UUID, schema: SearchStrategyUpdate, org_id: uuid.UUID,
    ) -> SearchStrategyResponse:
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        create_schema = SearchStrategyCreate(**schema.model_dump(exclude_unset=True))
        strategy = await self.repo.upsert(project_id, create_schema)
        logger.info("search_strategy_updated", project_id=project_id)
        return SearchStrategyResponse.model_validate(strategy)

    async def generate_strategy(self, project_id: uuid.UUID, org_id: uuid.UUID) -> SearchStrategyResponse:
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        topic = project.topic or project.name
        description = project.description or ""

        ai_result = await ai_generate(topic, description)

        if ai_result and ai_result.get("keywords_en"):
            keywords_en = ", ".join(ai_result.get("keywords_en", []))
            keywords_es = ", ".join(ai_result.get("keywords_es", []))
            boolean_queries = "\n".join(ai_result.get("boolean_queries", []))
            synonyms = ", ".join(ai_result.get("synonyms", []))
            sources = ", ".join(ai_result.get("sources_recommended", ["openalex"]))

            logger.info("search_strategy_ai_generated", project_id=project_id, keywords_en=keywords_en[:100])
        else:
            en_kw, es_kw = self._generate_keywords(topic)
            keywords_en = ", ".join(sorted(en_kw))
            keywords_es = ", ".join(sorted(es_kw))
            boolean_queries = None
            synonyms = ", ".join(self._collect_synonyms(en_kw | es_kw))
            sources = "openalex"

            logger.info("search_strategy_stub_generated", project_id=project_id, reason="no_ai_key_or_result")

        schema = SearchStrategyCreate(
            keywords_en=keywords_en,
            keywords_es=keywords_es,
            boolean_queries=boolean_queries,
            synonyms=synonyms,
            sources_selected=sources,
            generated_by_ai=bool(ai_result and ai_result.get("keywords_en")),
        )
        strategy = await self.repo.upsert(project_id, schema)
        return SearchStrategyResponse.model_validate(strategy)

    @staticmethod
    def _generate_keywords(topic: str) -> tuple[set[str], set[str]]:
        clean = topic.lower().strip()
        for ch in ".,;:!?\"'()[]":
            clean = clean.replace(ch, " ")
        words = set(w.strip() for w in clean.split() if w.strip())

        es_vowels = set("áéíóúñ")
        en_kw: set[str] = set()
        es_kw: set[str] = set()

        for word in words:
            if any(c in es_vowels for c in word):
                es_kw.add(word)
            else:
                en_kw.add(word)

        return en_kw, es_kw

    @staticmethod
    def _collect_synonyms(words: set[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for word in sorted(words):
            syns = _SYNONYM_MAP.get(word, [])
            for s in syns:
                if s not in seen and s not in words:
                    seen.add(s)
                    result.append(s)
        return result
