"""OpenRouter-backed LLM provider."""

import logging
import time
from collections.abc import Sequence

import httpx

from backend.llm.base import LLMProvider, LLMProviderError


logger = logging.getLogger(__name__)


OPENROUTER_API_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

# Free slugs only: PulseX runs on an account with no credits, so a
# paid model would fail at billing rather than quietly cost money.
# OpenRouter retires free models and answers 404 for a slug it no
# longer serves, so more than one is listed and they are tried in
# order.
FREE_MODELS: tuple[str, ...] = (
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
)

DEFAULT_MODEL = FREE_MODELS[0]

FREE_SUFFIX = ":free"

MAX_ATTEMPTS = 3

RETRY_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

MODEL_UNAVAILABLE_STATUS_CODES = frozenset({400, 403, 404})

MAX_ERROR_BODY_CHARS = 500


class RetryableLLMError(LLMProviderError):
    """A provider failure that is worth retrying."""


class ModelUnavailableError(LLMProviderError):
    """This model cannot serve the request; another might."""


class OpenRouterProvider(LLMProvider):
    """Generate text through the OpenRouter API."""

    def __init__(
        self,
        api_key: str,
        model: str | Sequence[str] | None = None,
        *,
        timeout: float = 60.0,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        if not api_key:
            raise LLMProviderError(
                "OpenRouter API key is missing",
            )

        if isinstance(model, str):
            models: tuple[str, ...] = (model,)
        else:
            models = tuple(model or FREE_MODELS)

        if not models:
            raise LLMProviderError(
                "No OpenRouter model configured",
            )

        self._api_key = api_key
        self._models = models
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._active_model: str | None = None

    def generate(self, prompt: str) -> str:
        """Return the model's response to a prompt.

        Falls through to the next configured model when one
        cannot serve the request, and remembers the model that
        worked so later calls do not re-walk the list.
        """
        last_error: Exception | None = None

        for model in self._candidates():
            try:
                response = self._generate_with(prompt, model)
            except ModelUnavailableError as exc:
                logger.warning(
                    "Model unavailable, trying the next one: "
                    "model=%s error=%s",
                    model,
                    exc,
                )

                last_error = exc

                if self._active_model == model:
                    self._active_model = None

                continue

            self._active_model = model

            return response

        raise LLMProviderError(
            "No configured OpenRouter model could serve the "
            f"request (tried: {', '.join(self._models)})"
        ) from last_error

    def _candidates(self) -> list[str]:
        """Return models to try, the known-good one first."""
        if self._active_model is None:
            return list(self._models)

        return [
            self._active_model,
            *(
                model
                for model in self._models
                if model != self._active_model
            ),
        ]

    def _generate_with(
        self,
        prompt: str,
        model: str,
    ) -> str:
        """Call one model, retrying transient failures."""
        last_error: Exception | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._request(prompt, model)
            except RetryableLLMError as exc:
                last_error = exc

                if attempt == self._max_attempts:
                    break

                backoff = 2.0**attempt

                logger.warning(
                    "OpenRouter request failed, retrying in %.0fs "
                    "(attempt %d/%d): model=%s",
                    backoff,
                    attempt,
                    self._max_attempts,
                    model,
                )

                time.sleep(backoff)

        raise LLMProviderError(
            f"OpenRouter request failed for {model} after "
            f"{self._max_attempts} attempts"
        ) from last_error

    def _request(self, prompt: str, model: str) -> str:
        """Make one OpenRouter chat completion request."""
        payload = {
            "model": model,
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
            raise _status_error(exc, model) from exc
        except httpx.HTTPError as exc:
            raise RetryableLLMError(
                f"OpenRouter request failed: {exc}"
            ) from exc

        return _extract_content(data)


def _status_error(
    exc: httpx.HTTPStatusError,
    model: str,
) -> LLMProviderError:
    """Classify an HTTP error and keep the server's reason.

    A bare status code cannot distinguish a retired model from a
    request the account's data policy forbids, and both answer
    404, so the body is carried into the message.
    """
    status = exc.response.status_code

    message = (
        f"OpenRouter returned HTTP {status} for {model}: "
        f"{_response_detail(exc.response)}"
    )

    if status in RETRY_STATUS_CODES:
        return RetryableLLMError(message)

    if status in MODEL_UNAVAILABLE_STATUS_CODES:
        return ModelUnavailableError(message)

    return LLMProviderError(message)


def _response_detail(response: httpx.Response) -> str:
    """Return the server's explanation, however it is shaped."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:MAX_ERROR_BODY_CHARS] or "no body"

    if isinstance(body, dict):
        error = body.get("error")

        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])[:MAX_ERROR_BODY_CHARS]

        if isinstance(error, str):
            return error[:MAX_ERROR_BODY_CHARS]

    return str(body)[:MAX_ERROR_BODY_CHARS]


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
