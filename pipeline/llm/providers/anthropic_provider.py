"""
anthropic_provider.py — Concrete LLMProvider backed by the Anthropic API.

This is the ONLY file in the codebase that imports the `anthropic` package.
"""

import time
from typing import Optional

import anthropic

from pipeline.config import get_logger
from pipeline.llm.base import LLMProvider, LLMProviderError

logger = get_logger(__name__)

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 2


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, max_tokens: int = 200) -> str:
        last_exc: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text.strip()

            except anthropic.RateLimitError as exc:
                last_exc = exc
                wait = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Rate limited (attempt %d/%d) — retrying in %ds", attempt, MAX_RETRIES, wait
                )
                time.sleep(wait)

            except anthropic.APIConnectionError as exc:
                last_exc = exc
                wait = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Connection error (attempt %d/%d) — retrying in %ds", attempt, MAX_RETRIES, wait
                )
                time.sleep(wait)

            except anthropic.APIStatusError as exc:
                logger.error("Non-retryable API error: %s", exc)
                raise LLMProviderError(f"Anthropic API call failed: {exc}") from exc

        logger.error("Anthropic API call failed after %d attempts", MAX_RETRIES)
        raise LLMProviderError(
            f"Anthropic API call failed after {MAX_RETRIES} attempts"
        ) from last_exc