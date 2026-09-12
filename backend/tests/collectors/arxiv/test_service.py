"""Tests for the arXiv ingestion service."""

from unittest.mock import Mock

import pytest

from backend.collectors.arxiv.collector import (
    ArxivCollectionError,
)
from backend.collectors.arxiv.normalizer import (
    ArxivNormalizationError,
)
from backend.collectors.arxiv.parser import (
    ArxivParsingError,
    RawArxivEntry,
)
from backend.collectors.arxiv.service import (
    ArxivIngestionError,
    ArxivIngestionService,
)
from backend.config.arxiv import ArxivQueryConfig
from backend.models.research_paper import ResearchPaper


@pytest.fixture
def query_config() -> ArxivQueryConfig:
    """Return a test arXiv query configuration."""
    return ArxivQueryConfig(
        query="cat:cs.AI",
        max_results=10,
    )


@pytest.fixture
def raw_entry() -> RawArxivEntry:
    """Return a test raw arXiv entry."""
    return RawArxivEntry(
        id_url="https://arxiv.org/abs/2601.12345",
        title="Test AI Paper",
        summary="A test paper about artificial intelligence.",
        authors=["Alice Smith"],
        published="2026-01-10T08:30:00Z",
        updated="2026-01-15T12:00:00Z",
        categories=["cs.AI"],
        primary_category="cs.AI",
        abstract_url=(
            "https://arxiv.org/abs/2601.12345"
        ),
        pdf_url=(
            "https://arxiv.org/pdf/2601.12345"
        ),
    )


@pytest.fixture
def research_paper() -> ResearchPaper:
    """Return a test normalized research paper."""
    return ResearchPaper(
        id="2601.12345",
        arxiv_id="2601.12345",
        title="Test AI Paper",
        authors=["Alice Smith"],
        abstract="A test paper about artificial intelligence.",
        url="https://arxiv.org/abs/2601.12345",
        published_at="2026-01-10T08:30:00Z",
        updated_at="2026-01-15T12:00:00Z",
        categories=["cs.AI"],
        topics=[],
        importance_score=0.0,
        summary=None,
        why_it_matters=None,
    )


def test_ingest_runs_collection_parsing_and_normalization(
    query_config: ArxivQueryConfig,
    raw_entry: RawArxivEntry,
    research_paper: ResearchPaper,
) -> None:
    collector = Mock()
    parser = Mock()
    normalizer = Mock()

    collector.collect.return_value = [
        {"raw_xml": "<xml>test</xml>"},
    ]

    parser.parse.return_value = [raw_entry]
    normalizer.normalize.return_value = research_paper

    service = ArxivIngestionService(
        collector=collector,
        parser=parser,
        normalizer=normalizer,
    )

    result = service.ingest(query_config)

    assert result == [research_paper]

    collector.collect.assert_called_once_with(query_config)
    parser.parse.assert_called_once_with("<xml>test</xml>")
    normalizer.normalize.assert_called_once_with(raw_entry)


def test_ingest_normalizes_multiple_entries(
    query_config: ArxivQueryConfig,
    raw_entry: RawArxivEntry,
    research_paper: ResearchPaper,
) -> None:
    second_entry = RawArxivEntry(
        id_url="https://arxiv.org/abs/2601.67890",
        title="Second AI Paper",
        summary="Another test paper.",
        authors=["Bob Jones"],
        published="2026-01-11T08:30:00Z",
        updated="2026-01-16T12:00:00Z",
        categories=["cs.LG"],
        primary_category="cs.LG",
        abstract_url=(
            "https://arxiv.org/abs/2601.67890"
        ),
        pdf_url=(
            "https://arxiv.org/pdf/2601.67890"
        ),
    )

    second_paper = ResearchPaper(
        id="2601.67890",
        arxiv_id="2601.67890",
        title="Second AI Paper",
        authors=["Bob Jones"],
        abstract="Another test paper.",
        url="https://arxiv.org/abs/2601.67890",
        published_at="2026-01-11T08:30:00Z",
        updated_at="2026-01-16T12:00:00Z",
        categories=["cs.LG"],
        topics=[],
        importance_score=0.0,
        summary=None,
        why_it_matters=None,
    )

    collector = Mock()
    parser = Mock()
    normalizer = Mock()

    collector.collect.return_value = [
        {"raw_xml": "<xml>test</xml>"},
    ]

    parser.parse.return_value = [
        raw_entry,
        second_entry,
    ]

    normalizer.normalize.side_effect = [
        research_paper,
        second_paper,
    ]

    service = ArxivIngestionService(
        collector=collector,
        parser=parser,
        normalizer=normalizer,
    )

    result = service.ingest(query_config)

    assert result == [
        research_paper,
        second_paper,
    ]

    assert normalizer.normalize.call_count == 2


def test_ingest_wraps_collection_error(
    query_config: ArxivQueryConfig,
) -> None:
    collector = Mock()
    parser = Mock()
    normalizer = Mock()

    collector.collect.side_effect = ArxivCollectionError(
        "network failure"
    )

    service = ArxivIngestionService(
        collector=collector,
        parser=parser,
        normalizer=normalizer,
    )

    with pytest.raises(ArxivIngestionError):
        service.ingest(query_config)

    parser.parse.assert_not_called()
    normalizer.normalize.assert_not_called()


def test_ingest_wraps_parsing_error(
    query_config: ArxivQueryConfig,
) -> None:
    collector = Mock()
    parser = Mock()
    normalizer = Mock()

    collector.collect.return_value = [
        {"raw_xml": "<xml>test</xml>"},
    ]

    parser.parse.side_effect = ArxivParsingError(
        "invalid XML"
    )

    service = ArxivIngestionService(
        collector=collector,
        parser=parser,
        normalizer=normalizer,
    )

    with pytest.raises(ArxivIngestionError):
        service.ingest(query_config)

    normalizer.normalize.assert_not_called()


def test_ingest_wraps_normalization_error(
    query_config: ArxivQueryConfig,
    raw_entry: RawArxivEntry,
) -> None:
    collector = Mock()
    parser = Mock()
    normalizer = Mock()

    collector.collect.return_value = [
        {"raw_xml": "<xml>test</xml>"},
    ]

    parser.parse.return_value = [raw_entry]

    normalizer.normalize.side_effect = ArxivNormalizationError(
        "invalid paper"
    )

    service = ArxivIngestionService(
        collector=collector,
        parser=parser,
        normalizer=normalizer,
    )

    with pytest.raises(ArxivIngestionError):
        service.ingest(query_config)