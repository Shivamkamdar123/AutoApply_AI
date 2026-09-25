"""
Structured Logging Module
=========================
Uses structlog for structured JSON or formatted console logging.
Provides correlation IDs / run IDs across agent operations.
"""

import logging
import sys
from typing import Any, Optional
import structlog
from structlog.types import EventDict, Processor


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Ensure every log entry has a correlation_id if bound or defaulted."""
    if "correlation_id" not in event_dict:
        event_dict["correlation_id"] = "sys"
    return event_dict


def setup_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    """Configure structlog and standard logging."""
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_correlation_id,
    ]

    if json_format:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def get_logger(name: str = "autoapply", correlation_id: Optional[str] = None):
    """Retrieve a structlog logger, optionally pre-bound with a correlation ID."""
    logger = structlog.get_logger(name)
    if correlation_id:
        return logger.bind(correlation_id=correlation_id)
    return logger
