"""Celery tasks for AI-powered analysis: search strategy, technology extraction, trends, etc."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, UTC

from sqlalchemy import select, delete
from structlog import get_logger

from app.core.config import settings
from worker.app import app as celery_app
from worker.tasks.graph_tasks import get_worker_session_factory

logger = get_logger(__name__)


@celery_app.task(bind=True, name="run_analysis")
def run_analysis(self, project_id: str, topic: str) -> dict:
    """Run full AI analysis pipeline for a project."""
    return asyncio.run(_run_analysis_async(project_id, topic))


async def _run_analysis_async(project_id: str, topic: str) -> dict:
    """Async implementation of AI analysis."""
    pid = uuid.UUID(project_id)
    logger.info("analysis_task_started", project_id=project_id, topic=topic[:80])

    session_factory = get_worker_session_factory()
    async with session_factory() as db:
        try:
            from app.models.analysis import Technology, Trend, Actor, Opportunity
            from app.models.document import Document
            from app.models.project import SurveillanceProject
            from worker.ai.service import AnalysisService as AIAnalysis

            # Get project + documents
            project = await db.get(SurveillanceProject, pid)
            if project is None:
                return {"error": "Project not found", "status": "failed"}

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

            # Run AI analysis
            api_key = settings.GEMINI_API_KEY or settings.OPENAI_API_KEY or ""
            ai = AIAnalysis(api_key=api_key or None)
            result = await ai.analyze_project(
                topic=topic,
                corpus_text=corpus_text or topic,
                docs_summary=doc_summaries,
            )
            await ai.close()

            # Clear previous analysis
            for table in [Technology, Trend, Actor, Opportunity]:
                await db.execute(delete(table).where(table.project_id == pid))

            # Persist technologies
            techs = result.get("technologies", [])
            for t in techs.technologies if hasattr(techs, "technologies") else []:
                db.add(Technology(
                    project_id=pid, name=t.name[:255],
                    description=t.description, category=t.category,
                    confidence=t.confidence,
                ))

            # Persist trends
            trends = result.get("trends", [])
            for t in trends.trends if hasattr(trends, "trends") else []:
                db.add(Trend(
                    project_id=pid, name=t.name[:255],
                    description=t.description,
                    momentum=t.trend_type, trend_type=t.trend_type,
                ))

            # Persist actors
            actors = result.get("actors", [])
            for a in actors.actors if hasattr(actors, "actors") else []:
                db.add(Actor(
                    project_id=pid, name=a.name[:255],
                    actor_type=a.actor_type, country=a.country,
                ))

            # Persist opportunities
            opps = result.get("opportunities", [])
            for o in opps.opportunities if hasattr(opps, "opportunities") else []:
                db.add(Opportunity(
                    project_id=pid, title=o.title[:500],
                    description=o.description,
                    opportunity_type=o.opportunity_type,
                    priority=o.priority,
                ))

            # Update project status
            project.status = "report_ready"
            project.updated_at = datetime.now(UTC)

            await db.commit()

            t_count = len(techs.technologies) if hasattr(techs, "technologies") else 0
            tr_count = len(trends.trends) if hasattr(trends, "trends") else 0
            a_count = len(actors.actors) if hasattr(actors, "actors") else 0
            o_count = len(opps.opportunities) if hasattr(opps, "opportunities") else 0

            logger.info(
                "analysis_task_completed",
                project_id=project_id,
                technologies=t_count, trends=tr_count, actors=a_count, opps=o_count,
            )

            return {
                "status": "completed",
                "technologies": t_count,
                "trends": tr_count,
                "actors": a_count,
                "opportunities": o_count,
            }

        except Exception as exc:
            logger.exception("analysis_task_failed", project_id=project_id)
            return {"error": str(exc), "status": "failed"}
