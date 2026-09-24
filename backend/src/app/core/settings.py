from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Document Q&A API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )
    database_url: str = "postgresql+psycopg_async://postgres:postgres@localhost:55432/docqa"
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)
    redis_url: str = "redis://localhost:56379/0"
    s3_endpoint_url: str = "http://localhost:59000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "miniosecret"
    s3_bucket: str = "documents"
    s3_region: str = "us-east-1"
    development_user_id: UUID = UUID("00000000-0000-4000-8000-000000000001")
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    pipeline_version: str = "ingestion-v1"
    embedding_dimensions: int = Field(default=384, ge=1)
    embedding_provider: Literal["deterministic", "fastembed"] = "deterministic"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_source_repo: str = "qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q"
    embedding_revision: str = "faf4aa4225822f3bc6376869cb1164e8e3feedd0"
    answer_provider: Literal["deterministic", "ollama"] = "deterministic"
    answer_model: str = "qwen2.5:1.5b"
    ollama_base_url: str = "http://localhost:11434"
    chunk_size_tokens: int = Field(default=220, ge=32, le=2048)
    chunk_overlap_tokens: int = Field(default=40, ge=0, le=512)
    retrieval_dense_k: int = Field(default=12, ge=1, le=100)
    retrieval_lexical_k: int = Field(default=12, ge=1, le=100)
    retrieval_final_k: int = Field(default=6, ge=1, le=30)
    context_token_budget: int = Field(default=1800, ge=128, le=32000)
    celery_task_always_eager: bool = False
    request_timeout_seconds: float = Field(default=60.0, gt=0, le=300)

    @property
    def docs_enabled(self) -> bool:
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
