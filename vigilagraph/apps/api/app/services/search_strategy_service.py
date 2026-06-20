"""Search-strategy service — keyword configuration with MVP stub generation."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.search_strategy import SearchStrategy
from app.repositories.project_repository import ProjectRepository
from app.repositories.search_strategy_repository import SearchStrategyRepository
from app.schemas.search_strategy import SearchStrategyCreate, SearchStrategyResponse, SearchStrategyUpdate

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
    "seguridad informática": ["ciberseguridad", "security", "cybersecurity"],
    "datos": ["data", "big data", "analítica", "analysis"],
    "análisis": ["analysis", "analítica", "minería de datos"],
    "minería de datos": ["data mining", "analítica", "análisis"],
    "mejora": ["optimización", "perfeccionamiento", "improvement", "optimization"],
    "perfeccionamiento": ["mejora", "optimización", "improvement", "optimization"],
    "analítica": ["analysis", "análisis", "data", "minería de datos"],
}


class SearchStrategyService:
    """Business logic for search-strategy management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SearchStrategyRepository(db)
        self.project_repo = ProjectRepository(db)

    async def get_strategy(self, project_id: uuid.UUID, org_id: uuid.UUID) -> SearchStrategyResponse | None:
        """Return the strategy for *project_id*, or ``None``.

        Verifies the project belongs to *org_id* first.
        """
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        strategy = await self.repo.get_by_project(project_id)
        if strategy is None:
            return None
        return SearchStrategyResponse.model_validate(strategy)

    async def update_strategy(
        self, project_id: uuid.UUID, schema: SearchStrategyUpdate, org_id: uuid.UUID,
    ) -> SearchStrategyResponse:
        """Update an existing strategy (or create one from the payload)."""
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        create_schema = SearchStrategyCreate(**schema.model_dump(exclude_unset=True))
        strategy = await self.repo.upsert(project_id, create_schema)
        logger.info("search_strategy_updated", project_id=project_id)
        return SearchStrategyResponse.model_validate(strategy)

    async def generate_strategy(self, project_id: uuid.UUID, org_id: uuid.UUID) -> SearchStrategyResponse:
        """MVP stub: generate a keyword strategy from the project topic.

        Real AI-powered generation will be introduced in Change 4.
        """
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        topic = project.topic or project.name
        en_kw, es_kw = self._generate_keywords(topic)

        schema = SearchStrategyCreate(
            keywords_en=", ".join(sorted(en_kw)),
            keywords_es=", ".join(sorted(es_kw)),
            synonyms=", ".join(self._collect_synonyms(en_kw | es_kw)),
            generated_by_ai=True,
        )
        strategy = await self.repo.upsert(project_id, schema)
        logger.info("search_strategy_generated", project_id=project_id, topic=topic)
        return SearchStrategyResponse.model_validate(strategy)

    @staticmethod
    def _generate_keywords(topic: str) -> tuple[set[str], set[str]]:
        """MVP stub: extract Spanish and English keywords from a topic.

        This is intentionally naive — real AI generation is planned for
        Change 4 of the VigilaGraph IA roadmap.
        """
        # Simple cleaning and splitting
        clean = topic.lower().strip()
        for ch in ".,;:!?\"'()[]":
            clean = clean.replace(ch, " ")
        words = set(w.strip() for w in clean.split() if w.strip())

        # Heuristic: words with áéíóúñ are Spanish
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
        """Collect synonyms for the given set of words using the internal map."""
        seen: set[str] = set()
        result: list[str] = []
        for word in sorted(words):
            syns = _SYNONYM_MAP.get(word, [])
            for s in syns:
                if s not in seen and s not in words:
                    seen.add(s)
                    result.append(s)
        return result
