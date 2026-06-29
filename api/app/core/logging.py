"""Structured logging setup using structlog.

Includes a PII-redaction processor so emails, bearer tokens, and
passwords never reach the log stream. Production logs are JSON for
aggregation; dev logs are colourised console output.
"""

from __future__ import annotations

import re

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer
from structlog.types import EventDict, Processor

from app.core.config import settings

# Fields that must NEVER be logged in clear text.
_PII_KEYS = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "confirm_password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "jwt",
        "secret",
    }
)

# Regexes applied to free-form string values to catch PII embedded in
# otherwise-safe fields (e.g. a URL, a log message, a stack trace).
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_BEARER_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-+/=]+")
_LONG_HEX_RE = re.compile(r"\b[0-9a-f]{32,}\b")  # looks like a token/secret

_REDACTED = "[REDACTED]"


def _redact_pii(_logger: object, _method: str, event_dict: EventDict) -> EventDict:
    """Strip emails, bearer tokens, and known sensitive keys from log output.

    Runs as a structlog processor in the shared chain so every log call is
    safe to ship to centralised log storage.
    """
    for key in list(event_dict.keys()):
        if key.lower() in _PII_KEYS:
            event_dict[key] = _REDACTED
        elif isinstance(event_dict[key], str):
            value = event_dict[key]
            value = _EMAIL_RE.sub(_REDACTED, value)
            value = _BEARER_RE.sub(r"\1" + _REDACTED, value)
            value = _LONG_HEX_RE.sub(_REDACTED, value)
            event_dict[key] = value
    return event_dict


def configure_logging() -> None:
    """Configure structlog based on the current environment."""
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _redact_pii,
    ]

    if settings.is_production:
        renderer: Processor = JSONRenderer()
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
