"""Tests for daily brief generation."""

from datetime import UTC, datetime
from unittest.mock import Mock

from backend.llm.base import LLMProviderError
from backend.models import Article, ResearchPaper, Topic
from backend.services.brief import BriefGenerationService
from backend.services.content_processing import ProcessedItem


NOW = datetime(2026, 9, 16, 0, 0, tzinfo=UTC)


def create_article_item(article_id: str) -> ProcessedItem:
    """Create a processed news article."""
    return ProcessedItem(
        item=Article(
            id=article_id,
            title=f"Article {article_id}",
            source="Test Source",
            source_url="https://example.com",
            url=f"https://example.com/{article_id}",
            published_at="2026-09-15T00:00:00Z",
            fetched_at="2026-09-16T00:00:00Z",
            content_hash=f"hash-{article_id}",
        ),
        relevance_score=0.8,
        topics=[Topic.LLM],
        importance_score=0.7,
    )


def create_paper_item(paper_id: str) -> ProcessedItem:
    """Create a processed research paper."""
    return ProcessedItem(
        item=ResearchPaper(
            id=paper_id,
            arxiv_id=paper_id,
            title=f"Paper {paper_id}",
            authors=["Alice Smith"],
            abstract="An abstract.",
            url=f"https://arxiv.org/abs/{paper_id}",
            published_at="2026-09-15T00:00:00Z",
            updated_at="2026-09-15T00:00:00Z",
            categories=["cs.AI"],
        ),
        relevance_score=0.9,
        topics=[Topic.AI_RESEARCH],
        importance_score=0.9,
    )


def build_provider(response: str = "") -> Mock:
    """Build a provider returning a fixed response."""
    provider = Mock()

    provider.generate.return_value = response or (
        "INTRODUCTION: Good morning.\n"
        "SUMMARY: Agents were the theme."
    )

    return provider


def test_generate_splits_articles_and_papers() -> None:
    service = BriefGenerationService(
        provider=build_provider(),
    )

    brief = service.generate(
        [create_article_item("a1"), create_paper_item("p1")],
        now=NOW,
    )

    assert brief.article_ids == ["a1"]
    assert brief.paper_ids == ["p1"]


def test_generate_uses_the_model_opening() -> None:
    service = BriefGenerationService(
        provider=build_provider(),
    )

    brief = service.generate(
        [create_article_item("a1")],
        now=NOW,
    )

    assert brief.introduction == "Good morning."
    assert brief.summary == "Agents were the theme."


def test_generate_dates_and_titles_the_brief() -> None:
    service = BriefGenerationService(
        provider=build_provider(),
    )

    brief = service.generate(
        [create_article_item("a1")],
        now=NOW,
    )

    assert brief.id == "pulsex-2026-09-16"
    assert brief.date == NOW.date()
    assert brief.title == (
        "PulseX Daily Brief — September 16, 2026"
    )


def test_generate_caps_the_item_count() -> None:
    service = BriefGenerationService(
        provider=build_provider(),
        max_items=2,
    )

    brief = service.generate(
        [create_article_item(str(i)) for i in range(5)],
        now=NOW,
    )

    assert brief.article_ids == ["0", "1"]


def test_provider_failure_still_produces_a_brief() -> None:
    provider = Mock()

    provider.generate.side_effect = LLMProviderError(
        "unavailable",
    )

    service = BriefGenerationService(provider=provider)

    brief = service.generate(
        [create_article_item("a1"), create_paper_item("p1")],
        now=NOW,
    )

    assert brief.article_ids == ["a1"]
    assert "1 news article" in brief.summary
    assert "1 research paper" in brief.summary


def test_empty_day_still_produces_a_brief() -> None:
    provider = Mock()

    service = BriefGenerationService(provider=provider)

    brief = service.generate([], now=NOW)

    assert brief.article_ids == []
    assert brief.paper_ids == []
    assert brief.introduction
    assert brief.summary
    provider.generate.assert_not_called()


def test_unparsable_opening_falls_back() -> None:
    service = BriefGenerationService(
        provider=build_provider("no labels at all"),
    )

    brief = service.generate(
        [create_article_item("a1")],
        now=NOW,
    )

    assert "1 news article" in brief.summary
