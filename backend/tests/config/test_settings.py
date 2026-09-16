"""Tests for runtime settings."""

import pytest

from backend.config.settings import Settings


def build_settings(**overrides) -> Settings:
    """Build settings with the required secrets filled in."""
    return Settings(
        openrouter_api_key="llm-key",
        resend_api_key="mail-key",
        email_from="brief@pulsex.dev",
        email_to="reader@example.com",
        **overrides,
    )


def test_model_defaults_to_the_fallback_list() -> None:
    assert build_settings().openrouter_model is None


def test_free_models_are_accepted() -> None:
    settings = build_settings(
        openrouter_model="vendor/model:free",
    )

    assert settings.openrouter_model == "vendor/model:free"


def test_paid_models_are_rejected() -> None:
    """The account has no credits, so this must fail at startup."""
    with pytest.raises(ValueError, match="free model"):
        build_settings(openrouter_model="openai/gpt-4o")


def test_missing_secrets_fail_at_startup() -> None:
    with pytest.raises(ValueError):
        Settings(
            openrouter_api_key="",
            resend_api_key="mail-key",
            email_from="brief@pulsex.dev",
            email_to="reader@example.com",
        )
