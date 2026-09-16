"""Email delivery through Resend."""

import logging

import httpx


logger = logging.getLogger(__name__)


RESEND_API_URL = "https://api.resend.com/emails"

DEFAULT_TIMEOUT = 30.0


class EmailDeliveryError(Exception):
    """Raised when the daily brief cannot be sent."""


class ResendEmailSender:
    """Send the daily brief with the Resend API."""

    def __init__(
        self,
        api_key: str,
        sender: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise EmailDeliveryError(
                "Resend API key is missing",
            )

        self._api_key = api_key
        self._sender = sender
        self._timeout = timeout

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        html: str,
    ) -> str:
        """Send one email and return the Resend message id."""
        payload = {
            "from": self._sender,
            "to": [recipient],
            "subject": subject,
            "html": html,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            "Sending brief: recipient=%s subject=%s",
            recipient,
            subject,
        )

        try:
            with httpx.Client(
                timeout=self._timeout,
            ) as client:
                response = client.post(
                    RESEND_API_URL,
                    json=payload,
                    headers=headers,
                )

                response.raise_for_status()

                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.exception("Resend rejected the request")

            raise EmailDeliveryError(
                "Resend returned HTTP "
                f"{exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("Could not reach Resend")

            raise EmailDeliveryError(
                f"Could not reach Resend: {exc}"
            ) from exc

        message_id = data.get("id")

        if not message_id:
            raise EmailDeliveryError(
                "Resend response had no message id",
            )

        logger.info(
            "Brief sent: message_id=%s",
            message_id,
        )

        return message_id
