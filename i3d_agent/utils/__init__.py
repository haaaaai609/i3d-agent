"""
Utility functions and helpers for i3d-agent-system.

This package provides logging, telemetry, and other utility functions.
"""

from i3d_agent.utils.logger import ContextAdapter, JSONFormatter, bind_context, get_logger
from i3d_agent.utils.telemetry import (
    get_tracer,
    instrument_fastapi,
    instrument_httpx,
    setup_telemetry,
)

__all__ = [
    # Logger exports
    "get_logger",
    "bind_context",
    "JSONFormatter",
    "ContextAdapter",
    # Telemetry exports
    "setup_telemetry",
    "instrument_fastapi",
    "instrument_httpx",
    "get_tracer",
]
