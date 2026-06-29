"""Report service — generates HTML, Markdown, and PDF reports."""

from __future__ import annotations

import html
import json
import uuid
from datetime import datetime, UTC
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.models.analysis import Actor, Opportunity, Technology, Trend
from app.models.document import Document
from app.models.graph import GraphNode, GraphRun
from app.models.project import SurveillanceProject
from app.models.report import Report
from app.repositories.report_repository import ReportRepository
from app.services.audit_service import AuditContext, AuditEvent, AuditService

logger = get_logger(__name__)


def h(value: object) -> str:
    """HTML-escape any user-supplied value before interpolating into a template.

    Every interpolation of a document title, technology name, actor name,
    trend description, etc. into the HTML report MUST go through this helper.
    A document with title '<script>alert(1)</script>' will execute in any
    browser that opens the generated report without this.
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)

REPORT_TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title} — VigilaGraph IA</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; color: #1a1a1a; line-height: 1.6; }}
  h1 {{ color: #1a56db; border-bottom: 2px solid #1a56db; padding-bottom: 0.5rem; }}
  h2 {{ color: #374151; margin-top: 2rem; }}
  .meta {{ color: #6b7280; font-size: 0.9rem; }}
  .stat {{ display: inline-block; background: #f3f4f6; padding: 0.25rem 1rem; border-radius: 999px; margin: 0.25rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
  th, td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #e5e7eb; }}
  th {{ background: #f9fafb; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 0.125rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 500; }}
  .badge-emerging {{ background: #dbeafe; color: #1e40af; }}
  .badge-growing {{ background: #d1fae5; color: #065f46; }}
  .badge-declining {{ background: #fce7f3; color: #9d174d; }}
  .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; font-size: 0.8rem; color: #9ca3af; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <p class="meta">Generado el {date} | VigilaGraph IA</p>

  <h2>Resumen del proyecto</h2>
  <p><strong>Tema:</strong> {topic}</p>
  <p><strong>Descripción:</strong> {description}</p>
  <p><strong>Estado:</strong> {status}</p>

  <h2>Documentos</h2>
  <p>Total de documentos: <strong>{doc_count}</strong></p>
  {doc_table}

  <h2>Tecnologías identificadas</h2>
  {tech_table}

  <h2>Tendencias</h2>
  {trend_table}

  <h2>Actores clave</h2>
  {actor_table}

  <h2>Oportunidades</h2>
  {opp_table}

  <div class="footer">
    <p>Reporte generado automáticamente por VigilaGraph IA.</p>
  </div>
</body>
</html>"""


class ReportService:
    """Generates surveillance reports from project data."""

    def __init__(self, db: AsyncSession, audit_context: AuditContext | None = None) -> None:
        self.db = db
        self.repo = ReportRepository(db)
        self.audit = AuditService()
        self.audit_context = audit_context or AuditContext()

    async def list_by_project(
        self, project_id: uuid.UUID, *, page: int = 1, page_size: int = 50,
    ) -> tuple[list[Report], int]:
        return await self.repo.list_by_project(project_id, page=page, page_size=page_size)

    async def get(self, report_id: uuid.UUID, project_id: uuid.UUID) -> Report | None:
        report = await self.repo.get(report_id)
        if report and report.project_id != project_id:
            return None
        return report

    async def generate(
        self,
        project_id: uuid.UUID,
        title: str | None = None,
        report_type: str = "complete",
        report_id: uuid.UUID | None = None,
        *,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
    ) -> Report:
        """Generate a report synchronously. Returns the Report record."""
        # 1. Get project
        project = await self.db.get(SurveillanceProject, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        report_title = title or f"Reporte de vigilancia — {project.name}"

        # 2. Create or reuse report record
        if report_id:
            report = await self.repo.get(report_id)
            if report is None:
                raise HTTPException(status_code=404, detail="Informe no encontrado")
        else:
            report = Report(
                project_id=project_id,
                title=report_title,
                report_type=report_type,
                format="html",
                status="generating",
            )
            self.db.add(report)
            await self.db.flush()
            await self.db.refresh(report)

        try:
            # 3. Collect data
            docs = (await self.db.execute(
                select(Document).where(Document.project_id == project_id).limit(500)
            )).scalars().all()

            technologies = (await self.db.execute(
                select(Technology).where(Technology.project_id == project_id)
            )).scalars().all()

            trends = (await self.db.execute(
                select(Trend).where(Trend.project_id == project_id)
            )).scalars().all()

            actors = (await self.db.execute(
                select(Actor).where(Actor.project_id == project_id)
            )).scalars().all()

            opportunities = (await self.db.execute(
                select(Opportunity).where(Opportunity.project_id == project_id)
            )).scalars().all()

            # 4. Generate HTML
            from pathlib import Path as FsPath

            storage = Path(settings.STORAGE_LOCAL_PATH) / "reports" / str(report.id)
            storage.mkdir(parents=True, exist_ok=True)

            html_content = self._render_html(
                title=report_title,
                topic=project.topic,
                description=project.description or "",
                status=project.status,
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                docs=docs,
                technologies=technologies,
                trends=trends,
                actors=actors,
                opportunities=opportunities,
            )

            html_path = storage / f"{report.id}.html"
            html_path.write_text(html_content, encoding="utf-8")

            # 4b. Generate PDF from HTML (optional — graceful if weasyprint unavailable)
            pdf_path = None
            try:
                from weasyprint import HTML

                pdf_path = storage / f"{report.id}.pdf"
                HTML(string=html_content).write_pdf(str(pdf_path))
                logger.info("report_pdf_generated", report_id=str(report.id))
            except ImportError:
                logger.info("report_pdf_skipped", report_id=str(report.id), reason="weasyprint_not_installed")
            except Exception as exc:
                logger.warning("report_pdf_failed", report_id=str(report.id), error=str(exc))

            # 5. Generate Markdown
            md_content = self._render_markdown(
                title=report_title,
                topic=project.topic,
                description=project.description or "",
                status=project.status,
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                docs=docs,
                technologies=technologies,
                trends=trends,
                actors=actors,
                opportunities=opportunities,
            )
            md_path = storage / f"{report.id}.md"
            md_path.write_text(md_content, encoding="utf-8")

            # 6. Update report
            report.status = "completed"
            report.html_path = str(html_path)
            report.markdown_path = str(md_path)
            if pdf_path:
                report.pdf_path = str(pdf_path)
            report.generated_at = datetime.now(UTC)
            await self.db.flush()
            await self.db.refresh(report)

            logger.info("report_generated", report_id=str(report.id), project_id=str(project_id))

            # Audit only on success — the failure path is logged via
            # structlog already and the report row carries the error.
            await self.audit.record(
                AuditEvent.REPORT_GENERATE,
                context=AuditContext(
                    actor_id=user_id,
                    organization_id=org_id,
                    ip=self.audit_context.ip,
                    user_agent=self.audit_context.user_agent,
                    request_id=self.audit_context.request_id,
                ),
                target_type="report",
                target_id=report.id,
                metadata={"project_id": str(project_id), "report_type": report_type},
            )

        except Exception as exc:
            report.status = "failed"
            report.error_message = str(exc)[:2000]
            await self.db.flush()
            logger.exception("report_generation_failed", report_id=str(report.id))

        return report

    async def delete(self, report_id: uuid.UUID, project_id: uuid.UUID) -> None:
        report = await self.repo.get(report_id)
        if report is None or report.project_id != project_id:
            raise HTTPException(status_code=404, detail="Informe no encontrado")
        await self.repo.delete(report_id)

    # ── Renderers ──────────────────────────────────────────────

    def _render_html(
        self,
        *,
        title: str,
        topic: str,
        description: str,
        status: str,
        date: str,
        docs: list,
        technologies: list,
        trends: list,
        actors: list,
        opportunities: list,
    ) -> str:
        def doc_rows():
            rows = ""
            for d in docs[:20]:
                rows += f"<tr><td>{h(d.title) or '?'}</td><td>{h(d.document_type) or 'N/A'}</td><td>{h(d.source_name) or 'manual'}</td></tr>"
            return rows

        def tech_rows():
            rows = ""
            for t in technologies:
                rows += f"<tr><td>{h(t.name)}</td><td>{h(t.category) or 'N/A'}</td><td>{h(t.trl_level) or 'N/A'}</td></tr>"
            return rows

        def trend_rows():
            rows = ""
            for t in trends:
                badge_class = {"emerging": "badge-emerging", "growing": "badge-growing", "declining": "badge-declining"}.get(t.momentum or "", "")
                rows += f"<tr><td>{h(t.name)}</td><td><span class='badge {badge_class}'>{h(t.momentum) or 'N/A'}</span></td><td>{h(t.description) or ''}</td></tr>"
            return rows

        def actor_rows():
            rows = ""
            for a in actors:
                rows += f"<tr><td>{h(a.name)}</td><td>{h(a.actor_type) or 'N/A'}</td><td>{h(a.country) or 'N/A'}</td></tr>"
            return rows

        def opp_rows():
            rows = ""
            for o in opportunities:
                rows += f"<tr><td>{h(o.title)}</td><td>{h(o.opportunity_type) or 'N/A'}</td><td>{h(o.priority) or 'N/A'}</td></tr>"
            return rows

        return REPORT_TEMPLATE_HTML.format(
            title=h(title),
            date=h(date),
            topic=h(topic),
            description=h(description),
            status=h(status),
            doc_count=len(docs),
            doc_table=f"<table><tr><th>Título</th><th>Tipo</th><th>Fuente</th></tr>{doc_rows()}</table>" if docs else "<p>Sin documentos</p>",
            tech_table=f"<table><tr><th>Tecnología</th><th>Categoría</th><th>TRL</th></tr>{tech_rows()}</table>" if technologies else "<p>Sin tecnologías identificadas</p>",
            trend_table=f"<table><tr><th>Tendencia</th><th>Dirección</th><th>Descripción</th></tr>{trend_rows()}</table>" if trends else "<p>Sin tendencias detectadas</p>",
            actor_table=f"<table><tr><th>Actor</th><th>Tipo</th><th>País</th></tr>{actor_rows()}</table>" if actors else "<p>Sin actores identificados</p>",
            opp_table=f"<table><tr><th>Oportunidad</th><th>Tipo</th><th>Prioridad</th></tr>{opp_rows()}</table>" if opportunities else "<p>Sin oportunidades detectadas</p>",
        )

    def _render_markdown(
        self,
        *,
        title: str,
        topic: str,
        description: str,
        status: str,
        date: str,
        docs: list,
        technologies: list,
        trends: list,
        actors: list,
        opportunities: list,
    ) -> str:
        lines = [
            f"# {h(title)}",
            f"",
            f"Generado el {h(date)} | VigilaGraph IA",
            f"",
            f"## Resumen del proyecto",
            f"",
            f"- **Tema:** {h(topic)}",
            f"- **Descripción:** {h(description)}",
            f"- **Estado:** {status}",
            f"",
            f"## Documentos",
            f"",
            f"Total: {len(docs)}",
            f"",
        ]
        for d in docs[:20]:
            lines.append(f"- {h(d.title)} ({h(d.document_type) or 'N/A'}) [{h(d.source_name) or 'manual'}]")

        if technologies:
            lines.extend(["", "## Tecnologías identificadas", ""])
            lines.append("| Tecnología | Categoría | TRL |")
            lines.append("|-----------|----------|-----|")
            for t in technologies:
                lines.append(f"| {h(t.name)} | {h(t.category) or 'N/A'} | {h(t.trl_level) or 'N/A'} |")

        if trends:
            lines.extend(["", "## Tendencias", ""])
            lines.append("| Tendencia | Dirección | Descripción |")
            lines.append("|----------|----------|-------------|")
            for t in trends:
                lines.append(f"| {h(t.name)} | {h(t.momentum) or 'N/A'} | {h(t.description) or ''} |")

        if actors:
            lines.extend(["", "## Actores clave", ""])
            lines.append("| Actor | Tipo | País |")
            lines.append("|-------|------|------|")
            for a in actors:
                lines.append(f"| {h(a.name)} | {h(a.actor_type) or 'N/A'} | {h(a.country) or 'N/A'} |")

        if opportunities:
            lines.extend(["", "## Oportunidades", ""])
            lines.append("| Oportunidad | Tipo | Prioridad |")
            lines.append("|------------|------|-----------|")
            for o in opportunities:
                lines.append(f"| {h(o.title)} | {h(o.opportunity_type) or 'N/A'} | {h(o.priority) or 'N/A'} |")

        lines.extend(["", "", "---", "Reporte generado automáticamente por VigilaGraph IA."])
        return "\n".join(lines)
