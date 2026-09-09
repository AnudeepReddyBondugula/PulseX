"""
test_config.py — Unit tests for config.py

Run with: pytest tests/test_config.py
"""

import pytest
from pydantic import ValidationError

from pipeline import config


def test_rss_sources_within_spec_range():
    assert 6 <= len(config.RSS_SOURCES) <= 10, "Spec requires 6-10 RSS sources (Section 4.1)"


def test_arxiv_categories_at_least_four():
    assert len(config.ARXIV_CATEGORIES) >= 4, "Spec requires 4+ arXiv categories (Section 4.1)"


def test_free_tier_limits_match_spec():
    assert config.FREE_PAPER_EXPLANATIONS_PER_MONTH == 1
    assert config.FREE_NEWS_EXPLANATIONS_PER_MONTH == 2


def test_claude_model_is_haiku():
    assert config.CLAUDE_MODEL == "claude-haiku-4-5"


# --- Settings tests -------------------------------------------------------
# _env_file=None is required here: without it, pydantic-settings falls back
# to reading your real local .env file even after monkeypatch.delenv removes
# the OS environment variable, making the "missing key" tests falsely pass.

def test_settings_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        config.Settings(_env_file=None)


def test_settings_loads_when_api_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    settings = config.Settings(_env_file=None)
    assert settings.anthropic_api_key == "test-key-123"


def test_settings_optional_fields_default_none(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_PATH", raising=False)
    settings = config.Settings(_env_file=None)
    assert settings.firebase_service_account_path is None


# --- validate_pipeline_config tests ---------------------------------------
# These mock get_settings() directly rather than manipulating env vars, so
# they're immune to whatever is (or isn't) in the real local .env file.

def test_validate_pipeline_config_raises_without_api_key(monkeypatch):
    def _raise():
        raise ValidationError.from_exception_data("Settings", [])
    monkeypatch.setattr(config, "get_settings", _raise)
    with pytest.raises(ValidationError):
        config.validate_pipeline_config()


def test_validate_pipeline_config_passes_with_api_key(monkeypatch):
    fake_settings = config.Settings(_env_file=None, ANTHROPIC_API_KEY="test-key-123")
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    config.validate_pipeline_config()  # should not raise


def test_get_logger_returns_same_instance_on_reimport():
    logger1 = config.get_logger("pulsex.test")
    logger2 = config.get_logger("pulsex.test")
    assert logger1 is logger2   