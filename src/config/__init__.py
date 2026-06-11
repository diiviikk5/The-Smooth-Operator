"""Configuration module for The Smooth Operator.

Provides Pydantic Settings v2 configuration classes that load values
from environment variables and .env files.

Usage:
    from src.config import get_settings

    settings = get_settings()
    print(settings.database.url)
"""

from src.config.settings import (
    AppSettings,
    ChromaSettings,
    DatabaseSettings,
    EmailSettings,
    EmbeddingSettings,
    LLMSettings,
    MonitoringSettings,
    RedisSettings,
    Settings,
    get_settings,
)

__all__ = [
    "AppSettings",
    "ChromaSettings",
    "DatabaseSettings",
    "EmailSettings",
    "EmbeddingSettings",
    "LLMSettings",
    "MonitoringSettings",
    "RedisSettings",
    "Settings",
    "get_settings",
]
