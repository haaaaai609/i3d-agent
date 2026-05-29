"""
Logging utilities for i3d-agent-system.

This module provides structured logging with JSON and text format support,
including context binding for tenant/user/session tracking.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional

from i3d_agent.config.settings import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs logs as JSON with fields: timestamp, level, logger, message,
    module, function, line, and optional context (tenant_id, user_id, session_id).
    """

    def __init__(self) -> None:
        """Initialize JSON formatter."""
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add stack trace if present
        if record.stack_info:
            log_data["stack_trace"] = self.formatStack(record.stack_info)

        # Add optional context fields if present in record
        for field in ("tenant_id", "user_id", "session_id"):
            if hasattr(record, field):
                value = getattr(record, field)
                if value is not None:
                    log_data[field] = value

        return json.dumps(log_data)


class ContextAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context to each log record.

    Context fields: tenant_id, user_id, session_id
    """

    def __init__(self, logger: logging.Logger, extra: dict[str, Any]) -> None:
        """
        Initialize context adapter.

        Args:
            logger: The base logger
            extra: Context dict with optional tenant_id, user_id, session_id
        """
        super().__init__(logger, extra)

    def process(
        self, msg: Any, kwargs: dict[str, Any]
    ) -> tuple[Any, dict[str, Any]]:
        """
        Process log message to add context.

        Args:
            msg: The log message
            kwargs: Keyword arguments for log call

        Returns:
            Tuple of (message, updated_kwargs)
        """
        # Add context to extra in kwargs
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"].update(self.extra)
        return msg, kwargs


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Create or retrieve a logger instance.

    The logger is configured based on settings.LOG_LEVEL and settings.LOG_FORMAT.
    If settings.LOG_FORMAT is "json", uses JSONFormatter.
    If settings.LOG_FILE is set, also logs to file.

    Args:
        name: Logger name (defaults to calling module name)

    Returns:
        Configured logger instance
    """
    if name is None:
        name = "i3d_agent"

    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        # Format based on settings
        if settings.LOG_FORMAT.lower() == "json":
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Optional file handler
        if settings.LOG_FILE:
            file_handler = logging.FileHandler(settings.LOG_FILE)
            file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Prevent propagation to root logger
        logger.propagate = False

    return logger


def bind_context(
    logger: logging.Logger,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> ContextAdapter:
    """
    Bind context to a logger for multi-tenant/session tracking.

    Args:
        logger: Base logger instance
        tenant_id: Optional tenant ID for multi-tenancy
        user_id: Optional user ID for user tracking
        session_id: Optional session ID for request tracking

    Returns:
        ContextAdapter that adds context to all log messages
    """
    extra: dict[str, Any] = {}
    if tenant_id is not None:
        extra["tenant_id"] = tenant_id
    if user_id is not None:
        extra["user_id"] = user_id
    if session_id is not None:
        extra["session_id"] = session_id

    return ContextAdapter(logger, extra)
