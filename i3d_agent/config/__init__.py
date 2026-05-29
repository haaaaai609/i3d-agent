"""
Configuration module for i3d-agent-system.

This module exports the application settings which are loaded from
environment variables using pydantic-settings.
"""

from i3d_agent.config.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
