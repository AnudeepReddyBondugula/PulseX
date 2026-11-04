"""Top‑level LLM package.

Provides a tiny factory that returns the concrete OpenRouter implementation
configured via environment variables (through the project's Settings model).
All production code should import :func:`get_default_provider` instead of the
concrete class to keep the rest of the codebase independent of a specific
vendor.
"""

from __future__ import annotations

from .base import LLMProvider, LLMProviderError
from backend.config.settings import Settings, get_settings


def get_default_provider(config: Settings | None = None) -> LLMProvider:
    """Create the default LLM provider.

    If a Settings instance is provided (as in tests), it is used directly.
    Otherwise the global settings are loaded via ``get_settings()``.
    """
    cfg: Settings = config if config is not None else get_settings()
    # Lazy import to avoid circular import with Settings
    from .providers.openrouter import OpenRouterProvider
    return OpenRouterProvider(
        api_key=cfg.openrouter_api_key,
        model=cfg.openrouter_model,
    )
