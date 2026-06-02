"""
Application settings using pydantic-settings.

This module defines all configuration settings for the i3d-agent-system.
Settings are loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Information
    APP_NAME: str = Field(default="i3d-agent-system", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Deployment environment")

    # API Settings
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_PREFIX: str = Field(default="/api/v1", description="API route prefix")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/i3d_agent",
        description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_CACHE_TTL: int = Field(default=3600, description="Default cache TTL in seconds")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="Max Redis connections")

    # LLM Provider Settings
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    DASHSCOPE_API_KEY: str = Field(default="", description="DashScope API key (Alibaba Cloud)")
    DASHSCOPE_BASE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="DashScope base URL"
    )
    COHERE_API_KEY: str = Field(default="", description="Cohere API key")
    COHERE_RERANK_MODEL: str = Field(
        default="rerank-english-v2.0",
        description="Cohere rerank model"
    )
    DEFAULT_LLM_PROVIDER: str = Field(default="anthropic", description="Default LLM provider (anthropic, openai, dashscope)")
    DEFAULT_LLM_MODEL: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default LLM model"
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="Embedding model for vector search"
    )
    LLM_MAX_TOKENS: int = Field(default=4096, description="Max tokens for LLM responses")
    LLM_TEMPERATURE: float = Field(default=0.7, description="Default temperature for LLM")

    # Service URLs
    INFER_ENGINEER_URL: str = Field(
        default="http://localhost:8080",
        description="Inference engineer service URL"
    )
    SEARCH_CORE_URL: str = Field(
        default="http://localhost:8081",
        description="Search core service URL"
    )
    MINIO_API_URL: str = Field(
        default="http://localhost:9000",
        description="MinIO object storage API URL"
    )
    XXL_JOB_URL: str = Field(
        default="http://localhost:8080/xxl-job-admin",
        description="XXL-Job admin URL"
    )

    # Tenant Settings
    DEFAULT_TENANT: str = Field(default="default", description="Default tenant ID")
    SUPPORTED_TENANTS: str = Field(
        default="default,tenant1,tenant2",
        description="List of supported tenant IDs (comma-separated)"
    )

    @property
    def supported_tenants_list(self) -> List[str]:
        """Get SUPPORTED_TENANTS as a list."""
        return [t.strip() for t in self.SUPPORTED_TENANTS.split(",") if t.strip()]

    # Observability Settings
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        default="http://localhost:4318",
        description="OpenTelemetry OTLP exporter endpoint"
    )
    ENABLE_TRACING: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    SERVICE_NAME: str = Field(default="i3d-agent-system", description="Service name for tracing")

    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    LOG_FORMAT: str = Field(default="json", description="Log format (json, text)")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path (optional)")

    # Agent Settings
    MAX_AGENT_ITERATIONS: int = Field(default=50, description="Maximum agent iterations")
    AGENT_TIMEOUT_SECONDS: int = Field(default=300, description="Agent execution timeout")
    ENABLE_AGENT_REFLECTION: bool = Field(default=True, description="Enable agent self-reflection")

    # RAG Settings
    RAG_TOP_K_RESULTS: int = Field(default=5, description="Number of top results for RAG")
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Similarity threshold for RAG")
    VECTOR_DIMENSION: int = Field(default=1536, description="Vector embedding dimension")

    # Memory Settings
    MEMORY_MAX_ENTRIES: int = Field(default=1000, description="Max memory entries per session")
    MEMORY_TTL_HOURS: int = Field(default=24, description="Memory TTL in hours")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    RATE_LIMIT_PERIOD: int = Field(default=60, description="Rate limit period in seconds")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_list_string(cls, v: str | List[str]) -> List[str]:
        """Parse comma-separated string into list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        """Ensure log level is uppercase."""
        return v.upper() if isinstance(v, str) else v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://", "sqlite:///")):
            raise ValueError(
                "DATABASE_URL must start with postgresql://, postgresql+psycopg2://, or sqlite:///"
            )
        return v

    def get_database_url(self, async_driver: bool = False) -> str:
        """Get database URL with optional async driver."""
        if async_driver:
            return self.DATABASE_URL.replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://"
            ).replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Cached application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()
