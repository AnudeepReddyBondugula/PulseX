"""Tests for deterministic deduplication."""

from backend.models.article import Article
from backend.processors.deduplication.processor import (
    Deduplicator,
)


def create_article(
    *,
    article_id: str,
    title: str = "OpenAI Releases a New Model",
    url: str = "https://example.com/article",
    content_hash: str = "hash-1",
) -> Article:
    """Create a minimal test article."""
    return Article(
        id=article_id,
        title=title,
        source="Test Source",
        source_url="https://example.com",
        url=url,
        published_at="2026-01-01T00:00:00Z",
        fetched_at="2026-01-01T01:00:00Z",
        content_hash=content_hash,
    )


def test_deduplicate_keeps_unique_items() -> None:
    items = [
        create_article(
            article_id="1",
            title="First Article",
            url="https://example.com/1",
            content_hash="hash-1",
        ),
        create_article(
            article_id="2",
            title="Second Article",
            url="https://example.com/2",
            content_hash="hash-2",
        ),
    ]

    result = Deduplicator().deduplicate(items)

    assert result.unique == items
    assert result.duplicates == []


def test_deduplicate_removes_duplicate_content_hash() -> None:
    first = create_article(
        article_id="1",
        content_hash="same-hash",
    )

    second = create_article(
        article_id="2",
        title="Completely Different Title",
        url="https://example.com/different",
        content_hash="same-hash",
    )

    result = Deduplicator().deduplicate(
        [first, second],
    )

    assert result.unique == [first]
    assert result.duplicates == [second]


def test_deduplicate_removes_duplicate_url() -> None:
    first = create_article(
        article_id="1",
        title="First Title",
        content_hash="hash-1",
    )

    second = create_article(
        article_id="2",
        title="Different Title",
        content_hash="hash-2",
    )

    second = second.model_copy(
        update={
            "url": first.url,
        },
    )

    result = Deduplicator().deduplicate(
        [first, second],
    )

    assert result.unique == [first]
    assert result.duplicates == [second]


def test_deduplicate_removes_duplicate_normalized_title() -> None:
    first = create_article(
        article_id="1",
        title="OpenAI Releases a New Model",
        url="https://example.com/1",
        content_hash="hash-1",
    )

    second = create_article(
        article_id="2",
        title="  OPENAI   Releases a New Model  ",
        url="https://example.com/2",
        content_hash="hash-2",
    )

    result = Deduplicator().deduplicate(
        [first, second],
    )

    assert result.unique == [first]
    assert result.duplicates == [second]


def test_deduplicate_canonicalizes_url() -> None:
    first = create_article(
        article_id="1",
        url="https://example.com/article",
        content_hash="hash-1",
    )

    second = create_article(
        article_id="2",
        url="https://EXAMPLE.COM/article/",
        content_hash="hash-2",
    )

    result = Deduplicator().deduplicate(
        [first, second],
    )

    assert result.unique == [first]
    assert result.duplicates == [second]


def test_deduplicate_ignores_url_fragment() -> None:
    first = create_article(
        article_id="1",
        url="https://example.com/article#section-one",
        content_hash="hash-1",
    )

    second = create_article(
        article_id="2",
        url="https://example.com/article#section-two",
        content_hash="hash-2",
    )

    result = Deduplicator().deduplicate(
        [first, second],
    )

    assert result.unique == [first]
    assert result.duplicates == [second]


def test_deduplicate_preserves_first_occurrence() -> None:
    first = create_article(
        article_id="first",
        content_hash="same-hash",
    )

    second = create_article(
        article_id="second",
        content_hash="same-hash",
    )

    third = create_article(
        article_id="third",
        content_hash="same-hash",
    )

    result = Deduplicator().deduplicate(
        [first, second, third],
    )

    assert result.unique == [first]
    assert result.duplicates == [second, third]


def test_normalize_title_collapses_whitespace() -> None:
    title = "  OpenAI    Releases\nA New\tModel  "

    normalized = Deduplicator._normalize_title(title)

    assert normalized == "openai releases a new model"


def test_canonical_url_removes_fragment() -> None:
    url = (
        "HTTPS://EXAMPLE.COM/article/"
        "?source=test#section"
    )

    canonical = Deduplicator._canonical_url(url)

    assert canonical == (
        "https://example.com/article?source=test"
    )