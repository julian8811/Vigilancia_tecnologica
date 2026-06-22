"""Structured logging setup using structlog."""

from __future__ import annotations

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog based on the current environment."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_production:
        renderer: structlog.types.Processor = JSONRenderer()
    else:
        renderer = ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Wire structlog as the root logger so standard-library loggers benefit too.
    structlog.stdlib.ProcessorFormatter(
        processor=renderer,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger for the caller's module."""
    return structlog.get_logger(name or __name__)
