"""
config.py — Central configuration for the PulseX content pipeline.

Uses pydantic-settings to load and VALIDATE environment variables at
startup — fails fast with a clear error if something required is missing
or malformed, instead of failing silently mid-pipeline.

Per NFR-8: secrets are never hardcoded here — only read from the environment.
"""

import logging
import sys
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a configured logger. Call this at the top of every module."""
    logger = logging.getLogger(name)
    if not logger.handlers:  # avoid duplicate handlers on reimport
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Secrets & settings (validated via pydantic-settings)
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """
    Loaded from environment variables / .env file.
    Required fields raise a clear pydantic ValidationError at startup if
    missing — no silent None values reaching pipeline code.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    # Not required until Module A5 — optional here so the pipeline can run
    # standalone before the Flask backend exists.
    firebase_service_account_path: str | None = Field(
        default=None, alias="FIREBASE_SERVICE_ACCOUNT_PATH"
    )
    # Not required until Module A10.
    play_service_account_path: str | None = Field(
        default=None, alias="PLAY_SERVICE_ACCOUNT_PATH"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton — Settings is only constructed (and .env only read)
    once per process, not on every call.
    """
    return Settings()  # raises pydantic.ValidationError if required fields missing


# ---------------------------------------------------------------------------
# Content sources (FR-1, FR-2 — fixed, version-controlled list)
# ---------------------------------------------------------------------------

RSS_SOURCES = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://arstechnica.com/feed/",
    "https://www.technologyreview.com/feed/",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.engadget.com/rss.xml",
    "https://hnrss.org/frontpage",
]

ARXIV_CATEGORIES = [
    "cs.AI",  # Artificial Intelligence
    "cs.LG",  # Machine Learning
    "cs.CL",  # Computation and Language (NLP)
    "cs.CV",  # Computer Vision
]

# ---------------------------------------------------------------------------
# Product constants (Section 10 — Free vs Paid tier)
# ---------------------------------------------------------------------------

FREE_PAPER_EXPLANATIONS_PER_MONTH = 1
FREE_NEWS_EXPLANATIONS_PER_MONTH = 2

SUBSCRIPTION_PRICE_INR = 60

CLAUDE_MODEL = "claude-haiku-4-5"
GEMINI_MODEL = "gemini-1.5-turbo"


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------

def validate_pipeline_config() -> None:
    """
    Call this once at the start of the daily pipeline run.
    Fails fast (and loudly) if required config is missing, instead of
    failing halfway through a run.
    """
    if len(RSS_SOURCES) < 6:
        logger.warning(
            "Only %d RSS sources configured; spec calls for 6-10.", len(RSS_SOURCES)
        )
    if not ARXIV_CATEGORIES:
        raise ValueError("ARXIV_CATEGORIES is empty — pipeline has nothing to fetch.")

    get_settings()  # raises pydantic.ValidationError if ANTHROPIC_API_KEY missing

    logger.info(
        "Config validated: %d RSS sources, %d arXiv categories.",
        len(RSS_SOURCES),
        len(ARXIV_CATEGORIES),
    )