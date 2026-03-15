from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "internal-kb-backend"
    app_env: Literal["development", "staging", "production"] = "development"
    database_url: str = Field(
        default="postgresql+psycopg://kb:kb@postgres:5432/kb",
        alias="DATABASE_URL",
    )

    api_port: int = 8000

    embedding_provider: str = "openai"
    embedding_api_key: str = ""
    embedding_base_url: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_max_input_tokens: int = 8192
    embedding_request_max_total_tokens: int = 6000
    embedding_batch_size: int = 32
    embedding_timeout_seconds: int = 60

    chunk_target_tokens: int = 600
    chunk_max_tokens: int = 800
    chunk_overlap_tokens: int = 80

    search_vector_candidates: int = 40
    search_keyword_candidates: int = 40
    search_rrf_k: int = 60
    search_default_limit: int = 10
    search_max_limit: int = 50

    worker_poll_seconds: int = 2
    worker_idle_sleep_seconds: int = 2
    worker_max_attempts: int = 5

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+psycopg", "", 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
