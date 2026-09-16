"""Tests for the RSS ingestion service."""

from time import struct_time
from unittest.mock import Mock

import pytest

from backend.collectors.rss.collector import (
    RSSCollectionError,
)
from backend.collectors.rss.normalizer import (
    RSSNormalizationError,
    RSSNormalizer,
)
from backend.collectors.rss.service import (
    RSSIngestionError,
    RSSIngestionService,
)
from backend.models import Article, Source, SourceType


@pytest.fixture
def source() -> Source:
    """Return a test RSS source."""
    return Source(
        name="Test Source",
        feed_url="https://example.com/rss.xml",
        source_type=SourceType.NEWS,
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


def test_ingest_collects_and_normalizes(
    source: Source,
) -> None:
    collector = Mock()
    normalizer = Mock()

    collector.collect.return_value = [
        {"title": "one"},
        {"title": "two"},
    ]

    articles = [
        create_article("1"),
        create_article("2"),
    ]

    normalizer.normalize.side_effect = articles

    service = RSSIngestionService(
        collector=collector,
        normalizer=normalizer,
    )

    result = service.ingest(source)

    assert result == articles
    collector.collect.assert_called_once_with(source)
    assert normalizer.normalize.call_count == 2


def test_ingest_returns_empty_for_empty_feed(
    source: Source,
) -> None:
    collector = Mock()
    normalizer = Mock()

    collector.collect.return_value = []

    service = RSSIngestionService(
        collector=collector,
        normalizer=normalizer,
    )

    assert service.ingest(source) == []
    normalizer.normalize.assert_not_called()


def test_ingest_skips_malformed_entries(
    source: Source,
) -> None:
    collector = Mock()
    normalizer = Mock()

    collector.collect.return_value = [
        {"title": "good"},
        {"title": "bad"},
    ]

    article = create_article("1")

    normalizer.normalize.side_effect = [
        article,
        RSSNormalizationError("missing link"),
    ]

    service = RSSIngestionService(
        collector=collector,
        normalizer=normalizer,
    )

    assert service.ingest(source) == [article]


def test_ingest_wraps_collection_errors(
    source: Source,
) -> None:
    collector = Mock()
    normalizer = Mock()

    collector.collect.side_effect = RSSCollectionError(
        "unreachable",
    )

    service = RSSIngestionService(
        collector=collector,
        normalizer=normalizer,
    )

    with pytest.raises(RSSIngestionError):
        service.ingest(source)


def test_ingest_skips_entries_failing_validation(
    source: Source,
) -> None:
    """A relative link fails Article validation, not normalization."""
    collector = Mock()

    collector.collect.return_value = [
        {
            "title": "Bad link",
            "link": "not-a-url",
            "published_parsed": struct_time(
                (2026, 1, 1, 0, 0, 0, 0, 1, 0),
            ),
        },
    ]

    service = RSSIngestionService(
        collector=collector,
        normalizer=RSSNormalizer(),
    )

    assert service.ingest(source) == []
