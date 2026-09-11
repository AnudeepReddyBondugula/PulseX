from time import struct_time

import pytest

from backend.collectors.rss.normalizer import (
    RSSNormalizationError,
    RSSNormalizer,
)
from backend.models import Source, SourceType


def create_source() -> Source:
    return Source(
        name="Example",
        feed_url="https://example.com/feed.xml",
        source_type=SourceType.NEWS,
    )


def create_entry() -> dict:
    return {
        "title": "Example AI Article",
        "link": "https://example.com/article",
        "author": "Jane Doe",
        "summary": "An example article.",
        "published_parsed": struct_time(
            (
                2026,
                9,
                11,
                10,
                30,
                0,
                4,
                254,
                0,
            )
        ),
    }


def test_normalize_creates_article() -> None:
    normalizer = RSSNormalizer()

    article = normalizer.normalize(
        create_entry(),
        create_source(),
    )

    assert article.title == "Example AI Article"
    assert article.source == "Example"
    assert str(article.source_url) == (
        "https://example.com/feed.xml"
    )
    assert str(article.url) == (
        "https://example.com/article"
    )
    assert article.author == "Jane Doe"
    assert article.description == "An example article."
    assert article.published_at.year == 2026
    assert article.published_at.month == 9
    assert article.published_at.day == 11
    assert article.fetched_at.tzinfo is not None
    assert article.content_hash


def test_normalize_generates_deterministic_id() -> None:
    normalizer = RSSNormalizer()
    source = create_source()
    entry = create_entry()

    first = normalizer.normalize(entry, source)
    second = normalizer.normalize(entry, source)

    assert first.id == second.id


def test_normalize_generates_deterministic_content_hash() -> None:
    normalizer = RSSNormalizer()
    source = create_source()
    entry = create_entry()

    first = normalizer.normalize(entry, source)
    second = normalizer.normalize(entry, source)

    assert first.content_hash == second.content_hash


def test_normalize_requires_title() -> None:
    normalizer = RSSNormalizer()
    entry = create_entry()
    entry.pop("title")

    with pytest.raises(RSSNormalizationError):
        normalizer.normalize(entry, create_source())


def test_normalize_requires_link() -> None:
    normalizer = RSSNormalizer()
    entry = create_entry()
    entry.pop("link")

    with pytest.raises(RSSNormalizationError):
        normalizer.normalize(entry, create_source())


def test_normalize_requires_publication_date() -> None:
    normalizer = RSSNormalizer()
    entry = create_entry()
    entry.pop("published_parsed")

    with pytest.raises(RSSNormalizationError):
        normalizer.normalize(entry, create_source())


def test_normalize_optional_author() -> None:
    normalizer = RSSNormalizer()
    entry = create_entry()
    entry.pop("author")

    article = normalizer.normalize(
        entry,
        create_source(),
    )

    assert article.author is None