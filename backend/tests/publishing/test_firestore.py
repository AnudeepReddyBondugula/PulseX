"""Tests for publishing briefs to Firestore."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from backend.models import (
    Article,
    DailyBrief,
    ResearchPaper,
    Topic,
)
from backend.publishing.firestore import (
    BRIEFS_COLLECTION,
    BriefPublishError,
    FirestoreBriefPublisher,
)
from backend.services.content_processing import ProcessedItem


NOW = datetime(2026, 9, 18, 3, 0, tzinfo=UTC)


@pytest.fixture
def brief() -> DailyBrief:
    """Return a test brief."""
    return DailyBrief(
        id="pulsex-2026-09-18",
        date="2026-09-18",
        title="PulseX Daily Brief",
        introduction="Good morning.",
        summary="Agents were the theme.",
        generated_at=NOW,
        article_ids=["a1"],
        paper_ids=["p1"],
    )


def article_item(
    *,
    image_url: str | None = "https://example.com/hero.jpg",
) -> ProcessedItem:
    """Return a processed news article."""
    return ProcessedItem(
        item=Article(
            id="a1",
            title="A model shipped",
            source="OpenAI",
            source_url="https://openai.com",
            url="https://openai.com/a1",
            published_at=NOW,
            fetched_at=NOW,
            content_hash="hash-a1",
            author="Alice Smith",
            image_url=image_url,
            summary="It shipped.",
            why_it_matters="It is faster.",
        ),
        relevance_score=0.8,
        topics=[Topic.LLM],
        importance_score=0.7,
    )


def paper_item() -> ProcessedItem:
    """Return a processed research paper."""
    return ProcessedItem(
        item=ResearchPaper(
            id="p1",
            arxiv_id="2609.00001",
            title="On scaling",
            authors=["Bob Jones", "Carol White"],
            abstract="An abstract.",
            url="https://arxiv.org/abs/2609.00001",
            published_at=NOW,
            updated_at=NOW,
            categories=["cs.AI"],
            summary="They scaled things.",
        ),
        relevance_score=0.9,
        topics=[Topic.AI_RESEARCH],
        importance_score=0.9,
    )


def published_payload(client: MagicMock) -> dict:
    """Return the document that was written."""
    document = client.collection.return_value.document

    return document.return_value.set.call_args.args[0]


def test_document_id_is_the_date(
    brief: DailyBrief,
) -> None:
    """A re-run for the same day must overwrite, not duplicate."""
    client = MagicMock()

    document_id = FirestoreBriefPublisher(client).publish(
        brief,
        [article_item()],
    )

    assert document_id == "2026-09-18"

    client.collection.assert_called_once_with(
        BRIEFS_COLLECTION,
    )

    client.collection.return_value.document.assert_called_once_with(
        "2026-09-18",
    )


def test_brief_fields_are_published(
    brief: DailyBrief,
) -> None:
    client = MagicMock()

    FirestoreBriefPublisher(client).publish(
        brief,
        [article_item(), paper_item()],
    )

    payload = published_payload(client)

    assert payload["title"] == "PulseX Daily Brief"
    assert payload["introduction"] == "Good morning."
    assert payload["date"] == "2026-09-18"
    assert payload["articleCount"] == 1
    assert payload["paperCount"] == 1


def test_items_are_embedded_in_the_document(
    brief: DailyBrief,
) -> None:
    """One read per day, rather than a subcollection query."""
    client = MagicMock()

    FirestoreBriefPublisher(client).publish(
        brief,
        [article_item(), paper_item()],
    )

    items = published_payload(client)["items"]

    assert len(items) == 2
    assert [item["kind"] for item in items] == [
        "news",
        "paper",
    ]


def test_article_carries_its_image_and_source(
    brief: DailyBrief,
) -> None:
    client = MagicMock()

    FirestoreBriefPublisher(client).publish(
        brief,
        [article_item()],
    )

    item = published_payload(client)["items"][0]

    assert item["source"] == "OpenAI"
    assert item["imageUrl"] == "https://example.com/hero.jpg"
    assert item["authors"] == ["Alice Smith"]
    assert item["summary"] == "It shipped."
    assert item["whyItMatters"] == "It is faster."
    assert item["topics"] == ["LLM"]


def test_article_without_an_image_publishes_null(
    brief: DailyBrief,
) -> None:
    """The app needs the key present to branch on it."""
    client = MagicMock()

    FirestoreBriefPublisher(client).publish(
        brief,
        [article_item(image_url=None)],
    )

    item = published_payload(client)["items"][0]

    assert item["imageUrl"] is None


def test_paper_is_attributed_to_arxiv(
    brief: DailyBrief,
) -> None:
    """Papers have no source field of their own."""
    client = MagicMock()

    FirestoreBriefPublisher(client).publish(
        brief,
        [paper_item()],
    )

    item = published_payload(client)["items"][0]

    assert item["source"] == "arXiv"
    assert item["authors"] == ["Bob Jones", "Carol White"]
    assert item["imageUrl"] is None


def test_write_failure_is_wrapped(
    brief: DailyBrief,
) -> None:
    client = MagicMock()

    document = client.collection.return_value.document
    document.return_value.set.side_effect = RuntimeError(
        "permission denied",
    )

    with pytest.raises(BriefPublishError):
        FirestoreBriefPublisher(client).publish(
            brief,
            [article_item()],
        )
