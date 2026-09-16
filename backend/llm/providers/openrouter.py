"""OpenRouter-backed LLM provider."""

import logging
import time

import httpx

from backend.llm.base import LLMProvider, LLMProviderError


logger = logging.getLogger(__name__)


OPENROUTER_API_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

# OpenRouter's free tier is rate limited, and free model slugs are
# retired from time to time, so this is expected to be overridden
# through configuration when a model stops being available.
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

MAX_ATTEMPTS = 3

RETRY_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class OpenRouterProvider(LLMProvider):
    """Generate text through the OpenRouter API."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        *,
        timeout: float = 60.0,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        if not api_key:
            raise LLMProviderError(
                "OpenRouter API key is missing",
            )

        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_attempts = max_attempts

    def generate(self, prompt: str) -> str:
        """Return the model's response, retrying transient errors."""
        last_error: Exception | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._request(prompt)
            except LLMProviderError as exc:
                last_error = exc

                if not self._is_retryable(exc):
                    raise

                if attempt == self._max_attempts:
                    break

                backoff = 2.0**attempt

                logger.warning(
                    "OpenRouter request failed, retrying in %.0fs "
                    "(attempt %d/%d)",
                    backoff,
                    attempt,
                    self._max_attempts,
                )

                time.sleep(backoff)

        raise LLMProviderError(
            "OpenRouter request failed after "
            f"{self._max_attempts} attempts"
        ) from last_error

    @staticmethod
    def _is_retryable(error: Exception) -> bool:
        """Whether a failure is worth another attempt."""
        return isinstance(error, RetryableLLMError)

    def _request(self, prompt: str) -> str:
        """Make one OpenRouter chat completion request."""
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(
                timeout=self._timeout,
            ) as client:
                response = client.post(
                    OPENROUTER_API_URL,
                    json=payload,
                    headers=headers,
                )

                response.raise_for_status()

                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise _status_error(exc) from exc
        except httpx.HTTPError as exc:
            raise RetryableLLMError(
                f"OpenRouter request failed: {exc}"
            ) from exc

        return _extract_content(data)


class RetryableLLMError(LLMProviderError):
    """A provider failure that is worth retrying."""


def _status_error(
    exc: httpx.HTTPStatusError,
) -> LLMProviderError:
    """Classify an HTTP error as retryable or terminal."""
    status = exc.response.status_code

    message = (
        f"OpenRouter returned HTTP {status}"
    )

    if status in RETRY_STATUS_CODES:
        return RetryableLLMError(message)

    return LLMProviderError(message)


def _extract_content(data: dict) -> str:
    """Pull the message text out of an OpenRouter response."""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError(
            "OpenRouter response had no message content",
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError(
            "OpenRouter returned an empty response",
        )

    return content.strip()
