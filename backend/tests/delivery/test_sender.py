"""Tests for Resend email delivery."""

from unittest.mock import Mock, patch

import httpx
import pytest

from backend.delivery.sender import (
    EmailDeliveryError,
    ResendEmailSender,
)


def patch_post(response: httpx.Response) -> Mock:
    """Patch httpx.Client.post with one response."""
    client = Mock()
    client.post.return_value = response
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)

    return client


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
            "https://api.resend.com/emails",
        ),
    )


def test_missing_api_key_is_rejected() -> None:
    with pytest.raises(EmailDeliveryError):
        ResendEmailSender(api_key="", sender="a@b.com")


def test_send_returns_the_message_id() -> None:
    client = patch_post(
        build_response(200, {"id": "msg-1"}),
    )

    with patch("httpx.Client", return_value=client):
        sender = ResendEmailSender(
            api_key="key",
            sender="brief@pulsex.dev",
        )

        message_id = sender.send(
            recipient="reader@example.com",
            subject="Daily Brief",
            html="<p>Hello</p>",
        )

    assert message_id == "msg-1"


def test_send_posts_the_expected_payload() -> None:
    client = patch_post(
        build_response(200, {"id": "msg-1"}),
    )

    with patch("httpx.Client", return_value=client):
        ResendEmailSender(
            api_key="key",
            sender="brief@pulsex.dev",
        ).send(
            recipient="reader@example.com",
            subject="Daily Brief",
            html="<p>Hello</p>",
        )

    payload = client.post.call_args.kwargs["json"]

    assert payload["from"] == "brief@pulsex.dev"
    assert payload["to"] == ["reader@example.com"]
    assert payload["subject"] == "Daily Brief"
    assert payload["html"] == "<p>Hello</p>"


def test_rejected_request_raises() -> None:
    client = patch_post(build_response(422))

    with patch("httpx.Client", return_value=client):
        sender = ResendEmailSender(
            api_key="key",
            sender="brief@pulsex.dev",
        )

        with pytest.raises(EmailDeliveryError):
            sender.send(
                recipient="reader@example.com",
                subject="Daily Brief",
                html="<p>Hello</p>",
            )


def test_response_without_id_raises() -> None:
    client = patch_post(build_response(200, {}))

    with patch("httpx.Client", return_value=client):
        sender = ResendEmailSender(
            api_key="key",
            sender="brief@pulsex.dev",
        )

        with pytest.raises(EmailDeliveryError):
            sender.send(
                recipient="reader@example.com",
                subject="Daily Brief",
                html="<p>Hello</p>",
            )
