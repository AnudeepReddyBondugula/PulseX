"""Runtime settings loaded from the environment."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.llm.providers.openrouter import (
    AUTO_FREE_MODEL,
    FREE_SUFFIX,
)
from backend.notifications.fcm import DEFAULT_TOPIC


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

    # Unset means try the built-in free models in order. A value
    # here pins one model and disables that fallback.
    openrouter_model: str | None = None

    resend_api_key: str = Field(min_length=1)

    email_from: str = Field(min_length=1)
    email_to: str = Field(min_length=1)

    max_brief_items: int = Field(default=15, ge=1)

    # Unset disables Firestore publishing and the push
    # notification, leaving email as the only channel. The value
    # is the service account JSON itself, not a path, because the
    # only place this runs is a runner with no persistent disk.
    firebase_service_account_json: str | None = None

    fcm_topic: str = DEFAULT_TOPIC

    seen_store_path: str = "data/seen_items.json"


    @field_validator("openrouter_model")
    @classmethod
    def _reject_paid_models(
        cls,
        value: str | None,
    ) -> str | None:
        """Keep the account off models it cannot pay for.

        PulseX runs on an account with no credits, so a paid
        slug should fail here rather than at billing time.
        """
        if value is None:
            return None

        if value == AUTO_FREE_MODEL:
            return value

        if not value.endswith(FREE_SUFFIX):
            raise ValueError(
                f"openrouter_model must be '{AUTO_FREE_MODEL}' or "
                f"a free model ending in '{FREE_SUFFIX}', got: {value}"
            )

        return value


    @property
    def publishes_to_app(self) -> bool:
        """Whether the app channel is configured."""
        return bool(self.firebase_service_account_json)


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
