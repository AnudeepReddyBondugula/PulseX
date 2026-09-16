"""Tests for the end-to-end digest pipeline."""

from datetime import UTC, datetime
from unittest.mock import Mock

from backend.models import Article
from backend.services.collection import (
    CollectionFailure,
    CollectionResult,
)
from backend.services.content_processing import (
    ProcessedContent,
)
from backend.services.digest import (
    DigestPipeline,
    create_digest_pipeline,
)


def create_article(article_id: str) -> Article:
    """Create a test article."""
    return Article(
        id=article_id,
        title=f"Article {article_id}",
        source="Test Source",
        source_url="https://example.com",
        url=f"https://example.com/{article_id}",
        published_at="2026-01-01T00:00:00Z",
        fetched_at="2026-01-01T01:00:00Z",
        content_hash=f"hash-{article_id}",
    )


def test_run_feeds_collected_items_into_processing() -> None:
    collection = Mock()
    processing = Mock()

    article = create_article("1")

    collection.collect.return_value = CollectionResult(
        articles=[article],
    )

    processed = ProcessedContent(
        items=[],
        duplicates=[],
        irrelevant=[],
    )

    processing.process.return_value = processed

    now = datetime(2026, 1, 2, tzinfo=UTC)

    pipeline = DigestPipeline(
        collection_service=collection,
        processing_service=processing,
    )

    result = pipeline.run(now=now)

    processing.process.assert_called_once_with(
        [article],
        now=now,
    )

    assert result.processed is processed
    assert result.failures == []


def test_run_surfaces_collection_failures() -> None:
    collection = Mock()
    processing = Mock()

    failure = CollectionFailure(
        source="Broken",
        error="feed down",
    )

    collection.collect.return_value = CollectionResult(
        failures=[failure],
    )

    processing.process.return_value = ProcessedContent(
        items=[],
        duplicates=[],
        irrelevant=[],
    )

    pipeline = DigestPipeline(
        collection_service=collection,
        processing_service=processing,
    )

    result = pipeline.run()

    assert result.failures == [failure]
    processing.process.assert_called_once_with(
        [],
        now=None,
    )


def test_create_digest_pipeline_wires_defaults() -> None:
    pipeline = create_digest_pipeline()

    assert isinstance(pipeline, DigestPipeline)
