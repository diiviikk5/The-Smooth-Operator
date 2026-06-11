"""Application settings powered by Pydantic Settings v2.

All configuration is loaded from environment variables (with .env fallback).
Each subsystem has its own settings class for clean separation of concerns.
A top-level ``Settings`` class composes them all and is cached via ``get_settings()``.
"""

from __future__ import annotations

import enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Enumerations ─────────────────────────────────────────────────────────────


class EnvironmentType(str, enum.Enum):
    """Runtime environment selector."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, enum.Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LLMProvider(str, enum.Enum):
    """Supported LLM provider backends."""

    OPENAI = "openai"
    GOOGLE = "google"


# ── Subsystem Settings ───────────────────────────────────────────────────────


class DatabaseSettings(BaseSettings):
    """PostgreSQL database connection settings.

    Attributes:
        url: Async SQLAlchemy connection string.
        pool_size: Number of persistent connections in the pool.
        max_overflow: Maximum overflow connections above pool_size.
        echo: Whether to log all SQL statements (disable in production).
        pool_recycle: Seconds after which a connection is recycled.
        pool_pre_ping: If True, test connections for liveness on checkout.
    """

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str = Field(
        default="postgresql+asyncpg://smoothop:smoothop@localhost:5432/smoothop",
        description="Async PostgreSQL connection string.",
    )
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size.")
    max_overflow: int = Field(
        default=20, ge=0, le=200, description="Max overflow connections."
    )
    echo: bool = Field(default=False, description="Echo SQL statements to log.")
    pool_recycle: int = Field(
        default=3600, ge=60, description="Connection recycle interval in seconds."
    )
    pool_pre_ping: bool = Field(
        default=True, description="Test connection liveness before checkout."
    )

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Ensure the URL uses an async-compatible driver."""
        if not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            msg = (
                "DATABASE_URL must start with 'postgresql+asyncpg://' "
                "or 'sqlite+aiosqlite://' for async support."
            )
            raise ValueError(msg)
        return v


class RedisSettings(BaseSettings):
    """Redis connection and caching settings.

    Attributes:
        url: Redis connection URL.
        ttl: Default cache time-to-live in seconds.
        max_connections: Maximum connections in the pool.
    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL.")
    ttl: int = Field(default=3600, ge=1, description="Default cache TTL in seconds.")
    max_connections: int = Field(
        default=20, ge=1, le=500, description="Maximum Redis connections."
    )


class ChromaSettings(BaseSettings):
    """ChromaDB vector store settings.

    Attributes:
        host: ChromaDB server hostname.
        port: ChromaDB server port.
        collection_name: Default collection for lead embeddings.
    """

    model_config = SettingsConfigDict(env_prefix="CHROMA_")

    host: str = Field(default="localhost", description="ChromaDB server host.")
    port: int = Field(default=8100, ge=1, le=65535, description="ChromaDB server port.")
    collection_name: str = Field(
        default="lead_embeddings", description="Default vector collection name."
    )

    @property
    def endpoint(self) -> str:
        """Return the full ChromaDB HTTP endpoint."""
        return f"http://{self.host}:{self.port}"


class LLMSettings(BaseSettings):
    """LLM provider and model settings.

    Attributes:
        provider: LLM backend to use (openai or google).
        model: Model identifier (e.g. gpt-4o-mini, gemini-2.0-flash).
        temperature: Sampling temperature for generation.
        max_tokens: Maximum tokens in the generated response.
        api_key: API key for the configured provider.
        request_timeout: HTTP timeout in seconds for LLM API calls.
        max_retries: Number of automatic retries on transient failures.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: LLMProvider = Field(
        default=LLMProvider.OPENAI, description="LLM provider backend."
    )
    model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL", description="Model identifier.")
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature."
    )
    max_tokens: int = Field(default=2048, ge=1, le=128000, description="Max output tokens.")
    api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key for the LLM provider. Falls back to provider-specific env vars.",
    )
    request_timeout: int = Field(default=60, ge=5, description="HTTP timeout in seconds.")
    max_retries: int = Field(default=3, ge=0, le=10, description="Automatic retry count.")


class EmbeddingSettings(BaseSettings):
    """Embedding model settings for semantic search.

    Attributes:
        model_name: HuggingFace model identifier for sentence-transformers.
        dimension: Output embedding dimensionality.
        batch_size: Number of texts to embed in a single batch.
    """

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
        description="Sentence-transformer model name.",
    )
    dimension: int = Field(default=384, ge=1, description="Embedding vector dimension.")
    batch_size: int = Field(default=64, ge=1, le=1024, description="Embedding batch size.")


class EmailSettings(BaseSettings):
    """SMTP email delivery settings.

    Attributes:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (587 for STARTTLS, 465 for SSL).
        smtp_user: SMTP authentication username.
        smtp_password: SMTP authentication password.
        from_email: Default sender email address.
        daily_limit: Maximum emails to send per day (spam protection).
        use_tls: Whether to use STARTTLS.
    """

    model_config = SettingsConfigDict(env_prefix="")

    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host.")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP server port.")
    smtp_user: str = Field(default="", description="SMTP username.")
    smtp_password: SecretStr = Field(default=SecretStr(""), description="SMTP password.")
    from_email: str = Field(default="", description="Sender email address.")
    daily_limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        alias="EMAIL_DAILY_LIMIT",
        description="Daily email send cap.",
    )
    use_tls: bool = Field(default=True, description="Use STARTTLS for SMTP.")


class MonitoringSettings(BaseSettings):
    """Observability and monitoring settings.

    Attributes:
        langsmith_api_key: LangSmith API key for LLM tracing.
        langsmith_project: LangSmith project name.
        enable_tracing: Whether to enable LangSmith tracing.
        prometheus_port: Port for the Prometheus metrics endpoint.
        enable_prometheus: Whether to expose Prometheus metrics.
    """

    model_config = SettingsConfigDict(env_prefix="")

    langsmith_api_key: SecretStr = Field(
        default=SecretStr(""), description="LangSmith API key."
    )
    langsmith_project: str = Field(
        default="smooth-operator", description="LangSmith project name."
    )
    enable_tracing: bool = Field(
        default=False,
        description="Enable LangSmith tracing.",
    )
    prometheus_port: int = Field(
        default=9090, ge=1, le=65535, description="Prometheus metrics port."
    )
    enable_prometheus: bool = Field(
        default=True, description="Expose Prometheus metrics endpoint."
    )


class AppSettings(BaseSettings):
    """Top-level application settings.

    Attributes:
        environment: Runtime environment (development/staging/production).
        log_level: Minimum log level.
        api_host: Host to bind the API server.
        api_port: Port to bind the API server.
        debug: Enable debug mode (extra logging, stack traces).
    """

    model_config = SettingsConfigDict(env_prefix="")

    environment: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT, description="Runtime environment."
    )
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Minimum log level.")
    api_host: str = Field(default="0.0.0.0", description="API server bind host.")  # noqa: S104
    api_port: int = Field(default=8000, ge=1, le=65535, description="API server bind port.")
    debug: bool = Field(default=False, description="Enable debug mode.")

    @field_validator("debug", mode="before")
    @classmethod
    def infer_debug_from_environment(cls, v: bool, info: object) -> bool:  # noqa: ARG003
        """Auto-enable debug in development unless explicitly set."""
        return v


# ── Composite Settings ───────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Root settings object that composes all subsystem configurations.

    This is the single source of truth for application configuration.
    Access it via the cached ``get_settings()`` function.

    Example:
        >>> settings = get_settings()
        >>> settings.database.url
        'postgresql+asyncpg://smoothop:smoothop@localhost:5432/smoothop'
        >>> settings.llm.model
        'gpt-4o-mini'
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Sub-configurations — each loaded from their own env prefixes
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    # Provider-level API keys (convenience — also readable from LLM sub-config)
    openai_api_key: SecretStr = Field(default=SecretStr(""), description="OpenAI API key.")
    google_api_key: SecretStr = Field(default=SecretStr(""), description="Google AI API key.")

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production."""
        return self.app.environment == EnvironmentType.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if the application is running in development."""
        return self.app.environment == EnvironmentType.DEVELOPMENT

    @property
    def effective_llm_api_key(self) -> SecretStr:
        """Resolve the LLM API key from provider-specific keys if not set directly.

        Returns:
            The API key to use for LLM calls, resolved in order:
            1. ``llm.api_key`` (if non-empty)
            2. ``openai_api_key`` (if provider is OpenAI)
            3. ``google_api_key`` (if provider is Google)
        """
        if self.llm.api_key.get_secret_value():
            return self.llm.api_key
        if self.llm.provider == LLMProvider.OPENAI:
            return self.openai_api_key
        return self.google_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Settings are loaded once from environment variables / .env file
    and cached for the lifetime of the process.

    Returns:
        The fully-resolved ``Settings`` instance.
    """
    return Settings()
