"""Runtime settings loaded from the environment."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.llm.providers.openrouter import DEFAULT_MODEL


class Settings(BaseSettings):
    """Secrets and per-deployment configuration.

    Values come from the environment, or a local .env file when
    running outside CI. Nothing here has a usable default, so a
    missing secret fails at startup rather than mid-run.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = Field(min_length=1)
    openrouter_model: str = DEFAULT_MODEL

    resend_api_key: str = Field(min_length=1)

    email_from: str = Field(min_length=1)
    email_to: str = Field(min_length=1)

    max_brief_items: int = Field(default=15, ge=1)

    seen_store_path: str = "data/seen_items.json"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
