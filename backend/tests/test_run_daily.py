"""Tests for the daily run entry point."""

from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest

from backend.config.settings import Settings
from backend.delivery.sender import EmailDeliveryError
from backend.notifications.fcm import NotificationError
from backend.publishing.firestore import BriefPublishError
from backend.run_daily import run
from backend.services.collection import CollectionFailure
from backend.services.content_processing import (
    ProcessedContent,
)
from backend.services.digest import DigestResult


COLLABORATORS = (
    "create_digest_pipeline",
    "JSONSeenStore",
    "SummarizationService",
    "BriefGenerationService",
    "BriefRenderer",
    "ResendEmailSender",
    "OpenRouterProvider",
    "create_firestore_client",
    "FirestoreBriefPublisher",
    "FCMNotifier",
    "create_messaging",
)


@dataclass
class Harness:
    """The patched collaborators used by one run."""

    pipeline: Any
    seen_store: Any
    summarizer: Any
    sender: Any
    publisher: Any
    notifier: Any


@pytest.fixture
def settings() -> Settings:
    """Return test settings with the app channel off."""
    return Settings(
        openrouter_api_key="llm-key",
        resend_api_key="mail-key",
        email_from="brief@pulsex.dev",
        email_to="reader@example.com",
    )


@pytest.fixture
def app_settings() -> Settings:
    """Return test settings with the app channel on."""
    return Settings(
        openrouter_api_key="llm-key",
        resend_api_key="mail-key",
        email_from="brief@pulsex.dev",
        email_to="reader@example.com",
        firebase_service_account_json=(
            '{"type": "service_account"}'
        ),
    )


@pytest.fixture
def harness() -> Harness:
    """Patch every collaborator the entry point builds."""
    with ExitStack() as stack:
        mocks = {
            name: stack.enter_context(
                patch(f"backend.run_daily.{name}"),
            )
            for name in COLLABORATORS
        }

        yield Harness(
            pipeline=mocks[
                "create_digest_pipeline"
            ].return_value,
            seen_store=mocks[
                "JSONSeenStore"
            ].return_value,
            summarizer=mocks[
                "SummarizationService"
            ].return_value,
            sender=mocks[
                "ResendEmailSender"
            ].return_value,
            publisher=mocks[
                "FirestoreBriefPublisher"
            ].return_value,
            notifier=mocks["FCMNotifier"].return_value,
        )


def build_digest_result(
    *,
    considered: list | None = None,
    failures: list | None = None,
) -> DigestResult:
    """Build a digest result with an empty processed set."""
    return DigestResult(
        processed=ProcessedContent(
            items=[],
            duplicates=[],
            irrelevant=[],
        ),
        failures=failures or [],
        considered=considered or [],
    )


def test_successful_run_marks_items_seen(
    settings: Settings,
    harness: Harness,
) -> None:
    considered = [Mock()]

    harness.pipeline.run.return_value = build_digest_result(
        considered=considered,
    )

    harness.summarizer.summarize.return_value = [Mock()]

    assert run(settings) == 0

    harness.sender.send.assert_called_once()

    harness.seen_store.mark_seen.assert_called_once_with(
        considered,
    )


def test_failed_delivery_does_not_mark_items_seen(
    settings: Settings,
    harness: Harness,
) -> None:
    """Marking after a failed send would lose the day's content."""
    harness.pipeline.run.return_value = build_digest_result(
        considered=[Mock()],
    )

    harness.summarizer.summarize.return_value = [Mock()]

    harness.sender.send.side_effect = EmailDeliveryError(
        "rejected",
    )

    assert run(settings) == 1

    harness.seen_store.mark_seen.assert_not_called()


def test_empty_day_skips_sending(
    settings: Settings,
    harness: Harness,
) -> None:
    considered = [Mock()]

    harness.pipeline.run.return_value = build_digest_result(
        considered=considered,
    )

    harness.summarizer.summarize.return_value = []

    assert run(settings) == 0

    harness.sender.send.assert_not_called()

    harness.seen_store.mark_seen.assert_called_once_with(
        considered,
    )


def test_source_failures_do_not_stop_the_run(
    settings: Settings,
    harness: Harness,
) -> None:
    harness.pipeline.run.return_value = build_digest_result(
        failures=[
            CollectionFailure(
                source="Broken",
                error="feed down",
            ),
        ],
    )

    harness.summarizer.summarize.return_value = [Mock()]

    assert run(settings) == 0

    harness.sender.send.assert_called_once()


def test_send_uses_the_configured_recipient(
    settings: Settings,
    harness: Harness,
) -> None:
    harness.pipeline.run.return_value = build_digest_result()

    harness.summarizer.summarize.return_value = [Mock()]

    run(settings)

    assert (
        harness.sender.send.call_args.kwargs["recipient"]
        == "reader@example.com"
    )


def test_only_brief_sized_slice_is_summarized(
    settings: Settings,
    harness: Harness,
) -> None:
    """An LLM call per collected item would be mostly wasted."""
    considered = [Mock() for _ in range(50)]

    harness.pipeline.run.return_value = DigestResult(
        processed=ProcessedContent(
            items=considered,
            duplicates=[],
            irrelevant=[],
        ),
        failures=[],
        considered=considered,
    )

    harness.summarizer.summarize.return_value = [Mock()]

    run(settings)

    summarized = harness.summarizer.summarize.call_args.args[0]

    assert len(summarized) == settings.max_brief_items
    assert summarized == considered[: settings.max_brief_items]


def test_app_channel_is_skipped_when_unconfigured(
    settings: Settings,
    harness: Harness,
) -> None:
    """Email-only deployments must not need Firebase."""
    harness.pipeline.run.return_value = build_digest_result()

    harness.summarizer.summarize.return_value = [Mock()]

    assert run(settings) == 0

    harness.publisher.publish.assert_not_called()
    harness.notifier.notify.assert_not_called()
    harness.sender.send.assert_called_once()


def test_brief_is_published_and_announced(
    app_settings: Settings,
    harness: Harness,
) -> None:
    harness.pipeline.run.return_value = build_digest_result()

    summarized = [Mock()]
    harness.summarizer.summarize.return_value = summarized

    assert run(app_settings) == 0

    harness.publisher.publish.assert_called_once()
    harness.notifier.notify.assert_called_once()

    assert harness.notifier.notify.call_args.kwargs[
        "item_count"
    ] == len(summarized)


def test_publishing_precedes_the_notification(
    app_settings: Settings,
    harness: Harness,
) -> None:
    """Announcing a brief the app cannot read yet is useless."""
    order: list[str] = []

    harness.publisher.publish.side_effect = (
        lambda *a, **k: order.append("publish")
    )
    harness.notifier.notify.side_effect = (
        lambda *a, **k: order.append("notify")
    )

    harness.pipeline.run.return_value = build_digest_result()
    harness.summarizer.summarize.return_value = [Mock()]

    run(app_settings)

    assert order == ["publish", "notify"]


def test_failed_publish_does_not_mark_items_seen(
    app_settings: Settings,
    harness: Harness,
) -> None:
    """App readers would otherwise lose the day entirely."""
    harness.pipeline.run.return_value = build_digest_result(
        considered=[Mock()],
    )

    harness.summarizer.summarize.return_value = [Mock()]

    harness.publisher.publish.side_effect = (
        BriefPublishError("permission denied")
    )

    assert run(app_settings) == 1

    harness.seen_store.mark_seen.assert_not_called()
    harness.sender.send.assert_not_called()


def test_failed_notification_still_sends_and_marks(
    app_settings: Settings,
    harness: Harness,
) -> None:
    """The brief is readable; only the ping was lost."""
    considered = [Mock()]

    harness.pipeline.run.return_value = build_digest_result(
        considered=considered,
    )

    harness.summarizer.summarize.return_value = [Mock()]

    harness.notifier.notify.side_effect = NotificationError(
        "unauthorized",
    )

    assert run(app_settings) == 0

    harness.sender.send.assert_called_once()

    harness.seen_store.mark_seen.assert_called_once_with(
        considered,
    )
