"""Tests for the OpenRouter provider."""

from unittest.mock import Mock, patch

import httpx
import pytest

from backend.llm.base import LLMProviderError
from backend.llm.providers.openrouter import (
    OpenRouterProvider,
)


def build_response(
    status_code: int,
    payload: dict | None = None,
) -> httpx.Response:
    """Build an httpx response for a fake request."""
    return httpx.Response(
        status_code,
        json=payload or {},
        request=httpx.Request(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
        ),
    )


def patch_post(*responses: httpx.Response) -> Mock:
    """Patch httpx.Client.post with queued responses."""
    client = Mock()
    client.post.side_effect = responses
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)

    return client


def test_missing_api_key_is_rejected() -> None:
    with pytest.raises(LLMProviderError):
        OpenRouterProvider(api_key="")


def test_generate_returns_message_content() -> None:
    client = patch_post(
        build_response(
            200,
            {
                "choices": [
                    {"message": {"content": " Hello "}},
                ],
            },
        ),
    )

    with patch("httpx.Client", return_value=client):
        provider = OpenRouterProvider(api_key="key")

        assert provider.generate("prompt") == "Hello"


def test_generate_uses_the_configured_model() -> None:
    client = patch_post(
        build_response(
            200,
            {"choices": [{"message": {"content": "hi"}}]},
        ),
    )

    with patch("httpx.Client", return_value=client):
        provider = OpenRouterProvider(
            api_key="key",
            model="some/model:free",
        )

        provider.generate("prompt")

    payload = client.post.call_args.kwargs["json"]

    assert payload["model"] == "some/model:free"


def test_rate_limits_are_retried() -> None:
    client = patch_post(
        build_response(429),
        build_response(
            200,
            {"choices": [{"message": {"content": "hi"}}]},
        ),
    )

    with (
        patch("httpx.Client", return_value=client),
        patch("time.sleep"),
    ):
        provider = OpenRouterProvider(api_key="key")

        assert provider.generate("prompt") == "hi"

    assert client.post.call_count == 2


def test_client_errors_are_not_retried() -> None:
    client = patch_post(build_response(401))

    with (
        patch("httpx.Client", return_value=client),
        patch("time.sleep"),
    ):
        provider = OpenRouterProvider(api_key="key")

        with pytest.raises(LLMProviderError):
            provider.generate("prompt")

    assert client.post.call_count == 1


def test_retries_are_bounded() -> None:
    client = patch_post(
        build_response(503),
        build_response(503),
        build_response(503),
    )

    with (
        patch("httpx.Client", return_value=client),
        patch("time.sleep"),
    ):
        provider = OpenRouterProvider(api_key="key")

        with pytest.raises(LLMProviderError):
            provider.generate("prompt")

    assert client.post.call_count == 3


def test_empty_content_is_an_error() -> None:
    client = patch_post(
        build_response(
            200,
            {"choices": [{"message": {"content": "   "}}]},
        ),
    )

    with patch("httpx.Client", return_value=client):
        provider = OpenRouterProvider(api_key="key")

        with pytest.raises(LLMProviderError):
            provider.generate("prompt")


def test_malformed_response_is_an_error() -> None:
    client = patch_post(build_response(200, {"choices": []}))

    with patch("httpx.Client", return_value=client):
        provider = OpenRouterProvider(api_key="key")

        with pytest.raises(LLMProviderError):
            provider.generate("prompt")
