"""Tests for content collection orchestration."""

from unittest.mock import Mock

from backend.collectors.arxiv.service import (
    ArxivIngestionError,
)
from backend.collectors.rss.service import (
    RSSIngestionError,
)
from backend.config.arxiv import ArxivQueryConfig
from backend.models import (
    Article,
    ResearchPaper,
    Source,
    SourceType,
)
from backend.services.collection import CollectionService


def create_source(name: str) -> Source:
    """Create a test RSS source."""
    return Source(
        name=name,
        feed_url=f"https://example.com/{name}.xml",
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


def create_paper(paper_id: str) -> ResearchPaper:
    """Create a test research paper."""
    return ResearchPaper(
        id=paper_id,
        arxiv_id=paper_id,
        title=f"Paper {paper_id}",
        authors=["Alice Smith"],
        abstract="A test abstract.",
        url=f"https://arxiv.org/abs/{paper_id}",
        published_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        categories=["cs.AI"],
    )


def test_collect_gathers_articles_and_papers() -> None:
    rss = Mock()
    arxiv = Mock()

    article = create_article("1")
    paper = create_paper("2601.00001")

    rss.ingest.return_value = [article]
    arxiv.ingest.return_value = [paper]

    service = CollectionService(
        rss_service=rss,
        arxiv_service=arxiv,
    )

    result = service.collect(
        sources=[create_source("Feed")],
        queries=[ArxivQueryConfig(query="cat:cs.AI")],
    )

    assert result.articles == [article]
    assert result.papers == [paper]
    assert result.failures == []
    assert result.items == [article, paper]


def test_collect_continues_after_source_failure() -> None:
    rss = Mock()
    arxiv = Mock()

    article = create_article("2")

    rss.ingest.side_effect = [
        RSSIngestionError("feed down"),
        [article],
    ]

    arxiv.ingest.return_value = []

    service = CollectionService(
        rss_service=rss,
        arxiv_service=arxiv,
    )

    result = service.collect(
        sources=[
            create_source("Broken"),
            create_source("Healthy"),
        ],
        queries=[],
    )

    assert result.articles == [article]
    assert len(result.failures) == 1
    assert result.failures[0].source == "Broken"


def test_collect_records_arxiv_failures() -> None:
    rss = Mock()
    arxiv = Mock()

    arxiv.ingest.side_effect = ArxivIngestionError(
        "api error",
    )

    service = CollectionService(
        rss_service=rss,
        arxiv_service=arxiv,
    )

    result = service.collect(
        sources=[],
        queries=[ArxivQueryConfig(query="cat:cs.LG")],
    )

    assert result.papers == []
    assert result.failures[0].source == "arxiv:cat:cs.LG"


def test_collect_uses_configured_defaults() -> None:
    rss = Mock()
    arxiv = Mock()

    rss.ingest.return_value = []
    arxiv.ingest.return_value = []

    service = CollectionService(
        rss_service=rss,
        arxiv_service=arxiv,
    )

    service.collect()

    assert rss.ingest.called
    assert arxiv.ingest.called
