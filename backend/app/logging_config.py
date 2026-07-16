import logging
import sys

import structlog


def configure_logging(debug: bool, log_level: str = "INFO") -> None:
    """Configure structlog so every log line — from middleware, route
    handlers, and lifespan events — is emitted as a single JSON object.

    JSON always in production; a readable console renderer in debug
    mode for local dev. Stdlib logging (uvicorn's access/error logs)
    is routed through the same renderer so nothing bypasses JSON.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer = (
        structlog.dev.ConsoleRenderer()
        if debug
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Uvicorn's own loggers still go through stdlib logging.
    # Replace the root handler so they print as plain messages;
    # structlog's ConsoleRenderer/JSONRenderer already did the formatting
    # by the time structlog-based loggers call logging under the hood.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )