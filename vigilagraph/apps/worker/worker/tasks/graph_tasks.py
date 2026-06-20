"""Celery tasks for graphify knowledge-graph generation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, UTC
from pathlib import Path

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from worker.app import app as celery_app
from worker.graphify.adapter import GraphifyAdapter, GraphifyInput
from worker.graphify.importer import GraphDBImporter
from worker.graphify.parser import GraphJsonParser

logger = logging.getLogger(__name__)

# Database URL — in production this would come from shared config
DATABASE_URL = "postgresql+asyncpg://vigilagraph:vigilagraph@localhost:5432/vigilagraph"

# Create a separate engine for the worker (not sharing the API's engine)
worker_engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10)
worker_session_factory = async_sessionmaker(worker_engine, class_=AsyncSession, expire_on_commit=False)


class AsyncTask(Task):
    """Base class for Celery tasks that need async execution.

    Handles the async event loop lifecycle so individual tasks don't
    need to worry about it.
    """

    _loop: asyncio.AbstractEventLoop | None = None

    def run(self, *args, **kwargs):
        """Override ``run`` to provide an async context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            coro = self.async_run(*args, **kwargs)
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def async_run(self, *args, **kwargs):
        """Subclasses implement this instead of ``run``."""
        raise NotImplementedError


@celery_app.task(base=AsyncTask, bind=True, name="run_graphify")
async def run_graphify(self, project_id: str, run_id: str) -> dict:
    """Execute graphify for a project as a Celery task.

    Args:
        project_id: UUID of the surveillance project.
        run_id: UUID of the GraphRun record to update.

    Returns:
        A dict with the task result summary.
    """
    project_uuid = uuid.UUID(project_id)
    run_uuid = uuid.UUID(run_id)

    logger.info("graphify_task_started", project_id=project_id, run_id=run_id)

    async with worker_session_factory() as db:
        try:
            # 1. Resolve the GraphRun record
            from app.models.graph import GraphRun

            run = await db.get(GraphRun, run_uuid)
            if run is None:
                return {"error": f"GraphRun {run_id} not found", "status": "failed"}

            # 2. Determine input corpus path
            corpus_path = run.input_corpus_path
            if not corpus_path or not Path(corpus_path).exists():
                run.status = "failed"
                run.error_message = "Corpus path not found or not set"
                run.finished_at = datetime.now(UTC)
                await db.flush()
                return {"error": "Corpus path not found", "status": "failed"}

            # 3. Run graphify
            adapter = GraphifyAdapter()
            output_dir = str(Path(corpus_path).parent / f"graphify_output_{run_uuid}")
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            gx_input = GraphifyInput(
                input_path=corpus_path,
                output_dir=output_dir,
                timeout=3600,
            )

            output = await adapter.run_async(gx_input)

            if output.returncode != 0:
                run.status = "failed"
                run.error_message = output.error_message or "Graphify CLI failed"
                run.finished_at = datetime.now(UTC)
                await db.flush()
                logger.error("graphify_task_failed", run_id=run_id, error=output.error_message)
                return {"error": output.error_message, "status": "failed"}

            # 4. Parse the output graph.json
            graph_json_path = Path(output_dir) / "graph.json"
            if not graph_json_path.exists():
                run.status = "failed"
                run.error_message = "graph.json not found in output directory"
                run.finished_at = datetime.now(UTC)
                await db.flush()
                return {"error": "graph.json not found", "status": "failed"}

            parser = GraphJsonParser()
            parsed_graph = parser.parse_file(graph_json_path)

            # 5. Import into DB
            importer = GraphDBImporter(db, run_uuid)
            counts = await importer.import_graph(parsed_graph)

            # 6. Update run record
            run.status = "completed"
            run.finished_at = datetime.now(UTC)
            run.node_count = counts["nodes_inserted"]
            run.edge_count = counts["edges_inserted"]
            run.community_count = parsed_graph.community_count
            run.graph_json_path = str(graph_json_path)
            run.graphify_version = await adapter.get_version() or "unknown"
            run.stats = {
                **parsed_graph.stats,
                "nodes_inserted": counts["nodes_inserted"],
                "edges_inserted": counts["edges_inserted"],
            }
            run.output_path = output_dir

            # Check for HTML
            html_path = Path(output_dir) / "graph.html"
            if html_path.exists():
                run.graph_html_path = str(html_path)

            await db.flush()

            logger.info(
                "graphify_task_completed",
                run_id=run_id,
                nodes=counts["nodes_inserted"],
                edges=counts["edges_inserted"],
            )

            return {
                "status": "completed",
                "nodes": counts["nodes_inserted"],
                "edges": counts["edges_inserted"],
                "communities": parsed_graph.community_count,
                "output_dir": output_dir,
            }

        except Exception as exc:
            logger.exception("graphify_task_exception", run_id=run_id)
            try:
                from app.models.graph import GraphRun

                run = await db.get(GraphRun, run_uuid)
                if run:
                    run.status = "failed"
                    run.error_message = str(exc)[:2000]
                    run.finished_at = datetime.now(UTC)
                    await db.flush()
            except Exception:
                logger.exception("graphify_task_status_update_failed", run_id=run_id)

            return {"error": str(exc), "status": "failed"}
