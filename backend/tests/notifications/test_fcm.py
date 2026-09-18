"""Tests for the morning push notification."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from backend.models import DailyBrief
from backend.notifications.fcm import (
    DEFAULT_TOPIC,
    FCMNotifier,
    NotificationError,
    _notification_body,
)


@pytest.fixture
def brief() -> DailyBrief:
    """Return a test brief."""
    return DailyBrief(
        id="pulsex-2026-09-18",
        date="2026-09-18",
        title="PulseX Daily Brief",
        introduction="Good morning.",
        summary="Agents were the theme.",
        generated_at=datetime(2026, 9, 18, 3, tzinfo=UTC),
    )


def sent_message(messaging: MagicMock) -> MagicMock:
    """Return the message handed to send()."""
    return messaging.send.call_args.args[0]


def test_notify_returns_the_message_id(
    brief: DailyBrief,
) -> None:
    messaging = MagicMock()
    messaging.send.return_value = "projects/x/messages/1"

    notifier = FCMNotifier(messaging=messaging)

    assert (
        notifier.notify(brief, item_count=14)
        == "projects/x/messages/1"
    )


def test_topic_is_used_rather_than_device_tokens(
    brief: DailyBrief,
) -> None:
    """Topics avoid maintaining a device registry."""
    messaging = MagicMock()

    FCMNotifier(messaging=messaging).notify(
        brief,
        item_count=3,
    )

    assert (
        messaging.Message.call_args.kwargs["topic"]
        == DEFAULT_TOPIC
    )


def test_topic_can_be_overridden(
    brief: DailyBrief,
) -> None:
    messaging = MagicMock()

    FCMNotifier(messaging=messaging, topic="staging").notify(
        brief,
        item_count=3,
    )

    assert (
        messaging.Message.call_args.kwargs["topic"]
        == "staging"
    )


def test_payload_lets_the_app_open_the_right_day(
    brief: DailyBrief,
) -> None:
    """Tapping should land on card one of this brief."""
    messaging = MagicMock()

    FCMNotifier(messaging=messaging).notify(
        brief,
        item_count=14,
    )

    data = messaging.Message.call_args.kwargs["data"]

    assert data["briefId"] == "pulsex-2026-09-18"
    assert data["briefDate"] == "2026-09-18"
    assert data["itemCount"] == "14"


def test_data_values_are_strings(
    brief: DailyBrief,
) -> None:
    """FCM rejects non-string values in the data payload."""
    messaging = MagicMock()

    FCMNotifier(messaging=messaging).notify(
        brief,
        item_count=14,
    )

    data = messaging.Message.call_args.kwargs["data"]

    assert all(
        isinstance(value, str) for value in data.values()
    )


def test_body_counts_the_stories(
    brief: DailyBrief,
) -> None:
    messaging = MagicMock()

    FCMNotifier(messaging=messaging).notify(
        brief,
        item_count=14,
    )

    body = messaging.Notification.call_args.kwargs["body"]

    assert "14 stories" in body


def test_send_failure_is_wrapped(
    brief: DailyBrief,
) -> None:
    messaging = MagicMock()
    messaging.send.side_effect = RuntimeError("unauthorized")

    with pytest.raises(NotificationError):
        FCMNotifier(messaging=messaging).notify(
            brief,
            item_count=1,
        )


def test_body_is_singular_for_one_story() -> None:
    assert _notification_body(1) == (
        "1 story waiting this morning."
    )
