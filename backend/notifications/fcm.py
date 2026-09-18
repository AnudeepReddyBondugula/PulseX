"""Push notifications for the mobile app."""

import logging
from typing import Any

from backend.models import DailyBrief


logger = logging.getLogger(__name__)


DEFAULT_TOPIC = "daily_brief"

ANDROID_CHANNEL_ID = "daily_brief"


class NotificationError(Exception):
    """Raised when the morning notification cannot be sent."""


class FCMNotifier:
    """Announce a published brief over Firebase Cloud Messaging.

    Sends to a topic rather than to device tokens, so no device
    registry is needed: the app subscribes to the topic on first
    run and every installation receives the same message.
    """

    def __init__(
        self,
        messaging: Any,
        topic: str = DEFAULT_TOPIC,
    ) -> None:
        self._messaging = messaging
        self._topic = topic

    def notify(
        self,
        brief: DailyBrief,
        *,
        item_count: int,
    ) -> str:
        """Send the morning notification, returning its id."""
        body = _notification_body(item_count)

        logger.info(
            "Sending notification: topic=%s body=%s",
            self._topic,
            body,
        )

        try:
            message = self._messaging.Message(
                notification=self._messaging.Notification(
                    title="Your PulseX brief is ready",
                    body=body,
                ),
                # The app reads these to open the right day at
                # the first card.
                data={
                    "briefId": brief.id,
                    "briefDate": brief.date.isoformat(),
                    "itemCount": str(item_count),
                },
                android=self._messaging.AndroidConfig(
                    priority="high",
                    notification=(
                        self._messaging.AndroidNotification(
                            channel_id=ANDROID_CHANNEL_ID,
                            click_action=(
                                "FLUTTER_NOTIFICATION_CLICK"
                            ),
                        )
                    ),
                ),
                topic=self._topic,
            )

            message_id = self._messaging.send(message)
        except Exception as exc:
            logger.exception("Failed to send notification")

            raise NotificationError(
                "Failed to send the morning notification",
            ) from exc

        logger.info(
            "Notification sent: message_id=%s",
            message_id,
        )

        return message_id


def _notification_body(item_count: int) -> str:
    """Write the notification body for a story count."""
    if item_count == 1:
        return "1 story waiting this morning."

    return f"{item_count} stories waiting this morning."


def create_messaging() -> Any:
    """Return the Firebase messaging module.

    Firestore publishing initializes the Firebase app, so this
    only needs to hand back the module once that has happened.
    """
    try:
        from firebase_admin import messaging
    except ImportError as exc:
        raise NotificationError(
            "firebase-admin is not installed",
        ) from exc

    return messaging
