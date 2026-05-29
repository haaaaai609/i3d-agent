"""
I3D Agent System - A multi-agent AI system powered by LangGraph and FastAPI.

This package provides a comprehensive framework for building and deploying
AI agents with tools, memory management, RAG capabilities, and workflow orchestration.
"""

__version__ = "0.1.0"
__author__ = "I3D Team"
__license__ = "MIT"

# Import main components for easier access
from i3d_agent.config import settings
from i3d_agent.workflow.graph import I3DWorkflow

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "settings",
    "I3DWorkflow",
]
