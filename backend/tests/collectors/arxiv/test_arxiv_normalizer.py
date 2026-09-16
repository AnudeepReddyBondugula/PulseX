"""Tests for arXiv normalization."""

from datetime import UTC, datetime

from dataclasses import replace

import pytest

from backend.collectors.arxiv.normalizer import (
    ArxivNormalizer,
    ArxivNormalizationError,
)
from backend.collectors.arxiv.parser import RawArxivEntry


@pytest.fixture
def raw_entry() -> RawArxivEntry:
    """Return a valid raw arXiv entry."""
    return RawArxivEntry(
        id_url="https://arxiv.org/abs/2601.12345",
        title="A New Approach to Artificial Intelligence",
        summary=(
            "This paper presents a new approach "
            "to AI research."
        ),
        authors=[
            "Alice Smith",
            "Bob Jones",
        ],
        published="2026-01-10T08:30:00Z",
        updated="2026-01-15T12:00:00Z",
        categories=[
            "cs.AI",
            "cs.LG",
        ],
        primary_category="cs.AI",
        abstract_url=(
            "https://arxiv.org/abs/2601.12345"
        ),
        pdf_url=(
            "https://arxiv.org/pdf/2601.12345"
        ),
    )


def test_normalize_creates_research_paper(
    raw_entry: RawArxivEntry,
) -> None:
    normalizer = ArxivNormalizer()

    paper = normalizer.normalize(raw_entry)

    assert paper.id == "2601.12345"
    assert paper.arxiv_id == "2601.12345"

    assert paper.title == (
        "A New Approach to Artificial Intelligence"
    )

    assert paper.authors == [
        "Alice Smith",
        "Bob Jones",
    ]

    assert paper.abstract == (
        "This paper presents a new approach to AI research."
    )

    assert str(paper.url) == (
        "https://arxiv.org/abs/2601.12345"
    )

    assert paper.published_at == datetime(
        2026,
        1,
        10,
        8,
        30,
        tzinfo=UTC,
    )

    assert paper.updated_at == datetime(
        2026,
        1,
        15,
        12,
        0,
        tzinfo=UTC,
    )

    assert paper.categories == [
        "cs.AI",
        "cs.LG",
    ]


def test_normalize_keeps_ai_fields_at_defaults(
    raw_entry: RawArxivEntry,
) -> None:
    normalizer = ArxivNormalizer()

    paper = normalizer.normalize(raw_entry)

    assert paper.topics == []
    assert paper.importance_score == 0.0
    assert paper.summary is None
    assert paper.why_it_matters is None


def test_normalize_uses_id_url_when_abstract_url_is_missing(
    raw_entry: RawArxivEntry,
) -> None:
    
    entry = replace(
        raw_entry,
        abstract_url=None,
    )

    normalizer = ArxivNormalizer()

    paper = normalizer.normalize(entry)

    assert str(paper.url) == (
        "https://arxiv.org/abs/2601.12345"
    )


def test_normalize_preserves_arxiv_version(
    raw_entry: RawArxivEntry,
) -> None:
    entry = replace(
        raw_entry,
        id_url="https://arxiv.org/abs/2601.12345v2",
    )

    normalizer = ArxivNormalizer()

    paper = normalizer.normalize(entry)

    assert paper.id == "2601.12345v2"
    assert paper.arxiv_id == "2601.12345v2"


def test_normalize_rejects_invalid_published_timestamp(
    raw_entry: RawArxivEntry,
) -> None:
    entry = replace(
        raw_entry,
        updated="not-a-date",
    )

    normalizer = ArxivNormalizer()

    with pytest.raises(ArxivNormalizationError):
        normalizer.normalize(entry)


def test_normalize_rejects_invalid_updated_timestamp(
    raw_entry: RawArxivEntry,
) -> None:
    entry = replace(
        raw_entry,
        updated="not-a-date",
    )

    normalizer = ArxivNormalizer()

    with pytest.raises(ArxivNormalizationError):
        normalizer.normalize(entry)