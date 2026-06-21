"""Analysis runner — runs AI analysis directly, no Celery."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

logger = get_logger(__name__)


async def run_analysis(db: AsyncSession, project_id: str, topic: str) -> None:
    """Run AI analysis on project documents (replaces Celery task)."""
    pid = uuid.UUID(project_id)
    logger.info("analysis_started", project_id=project_id)

    try:
        from app.models.analysis import Technology, Trend, Actor, Opportunity
        from app.models.document import Document
        from app.models.project import SurveillanceProject
        from app.core.config import settings
        from worker.ai.service import AnalysisService as AIAnalysis

        project = await db.get(SurveillanceProject, pid)
        if project is None:
            return

        docs_result = await db.execute(
            select(Document).where(Document.project_id == pid).limit(100)
        )
        docs = docs_result.scalars().all()

        doc_summaries = [
            {"title": d.title or "", "abstract": d.abstract or ""}
            for d in docs
        ]
        corpus_text = "\n\n".join(
            f"Title: {d.title}\nAbstract: {d.abstract or ''}"
            for d in docs[:50]
        )

        api_key = settings.GEMINI_API_KEY or settings.OPENAI_API_KEY or ""
        ai = AIAnalysis(api_key=api_key or None)
        result = await ai.analyze_project(
            topic=topic,
            corpus_text=corpus_text or topic,
            docs_summary=doc_summaries,
        )
        await ai.close()

        for table in [Technology, Trend, Actor, Opportunity]:
            await db.execute(delete(table).where(table.project_id == pid))

        techs = result.get("technologies", [])
        if hasattr(techs, "technologies"):
            for t in techs.technologies:
                db.add(Technology(
                    project_id=pid, name=t.name[:255],
                    description=t.description, category=t.category,
                    confidence=t.confidence,
                ))
        elif isinstance(techs, list):
            for t in techs:
                db.add(Technology(
                    project_id=pid,
                    name=t.get("name", "")[:255],
                    description=t.get("description"),
                    category=t.get("category"),
                ))

        trends = result.get("trends", [])
        if hasattr(trends, "trends"):
            for t in trends.trends:
                db.add(Trend(
                    project_id=pid, name=t.name[:255],
                    description=t.description, trend_type=t.trend_type,
                    momentum=t.momentum or "stable",
                ))
        elif isinstance(trends, list):
            for t in trends:
                db.add(Trend(
                    project_id=pid,
                    name=t.get("name", "")[:255],
                    description=t.get("description"),
                    trend_type=t.get("trend_type"),
                    momentum=t.get("momentum", "stable"),
                ))

        actors = result.get("actors", [])
        if hasattr(actors, "actors"):
            for a in actors.actors:
                db.add(Actor(
                    project_id=pid, name=a.name[:255],
                    description=a.description, actor_type=a.actor_type,
                    country=a.country,
                ))
        elif isinstance(actors, list):
            for a in actors:
                db.add(Actor(
                    project_id=pid,
                    name=a.get("name", "")[:255],
                    description=a.get("description"),
                    actor_type=a.get("actor_type"),
                    country=a.get("country"),
                ))

        opportunities = result.get("opportunities", [])
        if hasattr(opportunities, "opportunities"):
            for o in opportunities.opportunities:
                db.add(Opportunity(
                    project_id=pid, name=o.name[:255],
                    description=o.description, opportunity_type=o.opportunity_type,
                    priority=o.priority or "medium",
                ))
        elif isinstance(opportunities, list):
            for o in opportunities:
                db.add(Opportunity(
                    project_id=pid,
                    name=o.get("name", "")[:255],
                    description=o.get("description"),
                    opportunity_type=o.get("opportunity_type"),
                    priority=o.get("priority", "medium"),
                ))

        await db.flush()
        await db.commit()
        logger.info("analysis_completed", project_id=project_id, techs=len(techs), trends=len(trends))

    except Exception as exc:
        logger.exception("analysis_failed", project_id=project_id)
