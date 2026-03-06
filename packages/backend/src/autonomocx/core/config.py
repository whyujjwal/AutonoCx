"""Application configuration loaded from environment variables via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object.

    Every value is loaded from an environment variable whose name matches the
    field name (case-insensitive).  A `.env` file placed next to the running
    process is also read automatically.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ────────────────────────────────────────────────────────
    app_name: str = "AutonoCX"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: SecretStr = Field(
        ..., description="Main application secret used for signing / encryption"
    )
    allowed_hosts: list[str] = ["*"]
    api_prefix: str = "/api/v1"

    # ── Server ─────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # ── Database (PostgreSQL + asyncpg) ────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/autonomocx"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_echo: bool = False

    # ── Redis ──────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0

    # ── JWT / Auth ─────────────────────────────────────────────────────
    jwt_secret_key: SecretStr = Field(
        default=None,
        description="Separate secret for JWT signing. Falls back to secret_key if empty.",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "autonomocx"
    jwt_audience: str = "autonomocx"

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def _default_jwt_secret(cls, v: str | None, info) -> str | None:  # noqa: N805
        """Fall back to SECRET_KEY when JWT_SECRET_KEY is not set."""
        return v  # resolved at runtime via property

    @property
    def effective_jwt_secret(self) -> str:
        if self.jwt_secret_key is not None:
            return self.jwt_secret_key.get_secret_value()
        return self.secret_key.get_secret_value()

    # ── LLM Providers ──────────────────────────────────────────────────
    openai_api_key: SecretStr | None = None
    openai_org_id: str | None = None
    openai_default_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_retries: int = 3
    openai_timeout: float = 60.0

    anthropic_api_key: SecretStr | None = None
    anthropic_default_model: str = "claude-sonnet-4-20250514"
    anthropic_max_retries: int = 3
    anthropic_timeout: float = 60.0

    default_llm_provider: Literal["openai", "anthropic"] = "openai"

    # ── Channel Configuration ──────────────────────────────────────────
    # Web widget
    widget_allowed_origins: list[str] = ["*"]

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr | None = None
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: SecretStr | None = None

    # Twilio (voice + SMS)
    twilio_account_sid: str = ""
    twilio_auth_token: SecretStr | None = None
    twilio_phone_number: str = ""
    twilio_webhook_url: str = ""

    # Slack
    slack_bot_token: SecretStr | None = None
    slack_signing_secret: SecretStr | None = None
    slack_app_id: str = ""

    # WhatsApp (Twilio-based)
    whatsapp_phone_number: str = ""

    # ── S3 / Object Storage ────────────────────────────────────────────
    s3_bucket_name: str = ""
    s3_region: str = "us-east-1"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_endpoint_url: str | None = None  # For MinIO / localstack
    s3_presigned_url_expiry: int = 3600

    # ── RAG / Vector Search ────────────────────────────────────────────
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.72
    rag_embedding_dimensions: int = 1536
    rag_reranker_enabled: bool = False

    # ── Guardrails & Safety ────────────────────────────────────────────
    guardrail_toxicity_threshold: float = 0.7
    guardrail_pii_detection_enabled: bool = True
    guardrail_hallucination_threshold: float = 0.6
    guardrail_off_topic_threshold: float = 0.5
    guardrail_max_input_tokens: int = 4096
    guardrail_max_output_tokens: int = 2048

    # ── Rate Limiting ──────────────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_default_rpm: int = 60  # requests per minute
    rate_limit_burst_size: int = 10

    # ── CORS ───────────────────────────────────────────────────────────
    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    cors_allow_credentials: bool = True
    cors_allowed_methods: list[str] = ["*"]
    cors_allowed_headers: list[str] = ["*"]

    # ── Misc ───────────────────────────────────────────────────────────
    sentry_dsn: str | None = None
    analytics_enabled: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()  # type: ignore[call-arg]
