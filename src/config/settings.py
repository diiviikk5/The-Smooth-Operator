"""Application settings using Pydantic Settings management.

Provides centralized configuration for all components of The Smooth Operator
including LLM providers, database connections, email services, and feature flags.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = {"env_prefix": "LLM_"}

    provider: str = Field(default="openai", description="LLM provider: openai, anthropic, local")
    model_name: str = Field(default="gpt-4o-mini", description="Model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    api_key: SecretStr = Field(default=SecretStr(""), description="API key for the LLM provider")
    api_base: Optional[str] = Field(default=None, description="Custom API base URL")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Max retries on failure")

    judge_model: str = Field(default="gpt-4o", description="Model for LLM-as-judge evaluations")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    embedding_dimensions: int = Field(default=1536, description="Embedding vector dimensions")


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = {"env_prefix": "DB_"}

    url: str = Field(default="sqlite:///./smoothop.db", description="Database URL")
    vector_store_type: str = Field(default="chroma", description="Vector store: chroma, pinecone, qdrant")
    vector_store_path: str = Field(default="./data/vector_store", description="Local vector store path")
    vector_store_collection: str = Field(default="leads", description="Default collection name")


class EmailSettings(BaseSettings):
    """Email service configuration."""

    model_config = {"env_prefix": "EMAIL_"}

    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: SecretStr = Field(default=SecretStr(""))
    from_email: str = Field(default="")
    from_name: str = Field(default="")
    daily_send_limit: int = Field(default=50, description="Max emails per day")
    tracking_domain: str = Field(default="", description="Custom tracking domain")
    warmup_enabled: bool = Field(default=True, description="Enable email warmup")


class ScrapingSettings(BaseSettings):
    """Web scraping configuration."""

    model_config = {"env_prefix": "SCRAPE_"}

    max_concurrent: int = Field(default=5, description="Max concurrent scraping tasks")
    timeout: int = Field(default=30, description="Scraping request timeout")
    rate_limit_per_second: float = Field(default=2.0, description="Max requests per second")
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; SmoothOperator/1.0; +https://example.com/bot)"
    )
    proxy_url: Optional[str] = Field(default=None, description="Proxy URL for scraping")
    respect_robots_txt: bool = Field(default=True)


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""

    model_config = {"env_prefix": "MONITORING_"}

    langsmith_api_key: SecretStr = Field(default=SecretStr(""))
    langsmith_project: str = Field(default="smooth-operator")
    langsmith_endpoint: str = Field(default="https://api.smith.langchain.com")
    prometheus_port: int = Field(default=9090)
    enable_tracing: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    wandb_project: str = Field(default="smooth-operator")
    wandb_api_key: SecretStr = Field(default=SecretStr(""))
    mlflow_tracking_uri: str = Field(default="./mlruns")


class TrainingSettings(BaseSettings):
    """Training pipeline configuration."""

    model_config = {"env_prefix": "TRAINING_"}

    output_dir: str = Field(default="./models/fine_tuned")
    data_dir: str = Field(default="./data/training")
    lora_r: int = Field(default=16, description="LoRA rank")
    lora_alpha: int = Field(default=32, description="LoRA alpha")
    lora_dropout: float = Field(default=0.05)
    learning_rate: float = Field(default=2e-4)
    num_epochs: int = Field(default=3)
    batch_size: int = Field(default=4)
    gradient_accumulation_steps: int = Field(default=4)
    warmup_ratio: float = Field(default=0.03)
    max_seq_length: int = Field(default=2048)
    use_4bit: bool = Field(default=True, description="Use 4-bit quantization (QLoRA)")
    use_flash_attention: bool = Field(default=False)


class CampaignDefaults(BaseSettings):
    """Default campaign configuration."""

    model_config = {"env_prefix": "CAMPAIGN_"}

    score_threshold: int = Field(default=60, description="Minimum lead score to proceed")
    email_framework: str = Field(default="AIDA", description="Default email framework")
    max_follow_ups: int = Field(default=3)
    follow_up_delay_days: int = Field(default=3)
    ab_test_variants: int = Field(default=3, description="Number of subject line variants")
    target_tone: str = Field(default="professional", description="Target email tone")
    max_email_words: int = Field(default=150)
    min_email_words: int = Field(default=50)


class Settings(BaseSettings):
    """Main application settings aggregating all sub-settings."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    app_name: str = Field(default="The Smooth Operator")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    environment: str = Field(default="development")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    scraping: ScrapingSettings = Field(default_factory=ScrapingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    training: TrainingSettings = Field(default_factory=TrainingSettings)
    campaign: CampaignDefaults = Field(default_factory=CampaignDefaults)

    # Cost tracking
    cost_alert_threshold_daily: float = Field(default=50.0, description="Daily cost alert in USD")
    cost_alert_threshold_monthly: float = Field(default=500.0)

    # Guardrails
    blocklist_path: str = Field(default="./data/blocklist.txt")
    pii_detection_enabled: bool = Field(default=True)
    rate_limit_enabled: bool = Field(default=True)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "testing"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings: The application settings singleton.
    """
    return Settings()
