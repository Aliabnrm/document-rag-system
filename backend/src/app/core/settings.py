from functools import lru_cache
from typing import Literal

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
    cors_origins: list[AnyHttpUrl] = Field(default_factory=lambda: [AnyHttpUrl("http://localhost:3000")])

    @property
    def docs_enabled(self) -> bool:
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
