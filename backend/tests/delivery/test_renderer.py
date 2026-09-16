"""Tests for daily brief HTML rendering."""

from datetime import UTC, datetime

from backend.delivery.renderer import BriefRenderer
from backend.models import (
    Article,
    DailyBrief,
    ResearchPaper,
    Topic,
)
from backend.services.content_processing import ProcessedItem


def create_brief() -> DailyBrief:
    """Create a test daily brief."""
    return DailyBrief(
        id="pulsex-2026-09-16",
        date="2026-09-16",
        title="PulseX Daily Brief — September 16, 2026",
        introduction="Good morning.",
        generated_at=datetime(2026, 9, 16, tzinfo=UTC),
        summary="Agents were the theme.",
    )


def create_article_item(
    *,
    title: str = "A model shipped",
    summary: str | None = "It shipped.",
    why: str | None = "It is faster.",
) -> ProcessedItem:
    """Create a processed news article."""
    return ProcessedItem(
        item=Article(
            id="a1",
            title=title,
            source="TechCrunch AI",
            source_url="https://example.com",
            url="https://example.com/a1",
            published_at="2026-09-15T00:00:00Z",
            fetched_at="2026-09-16T00:00:00Z",
            content_hash="hash-a1",
            summary=summary,
            why_it_matters=why,
        ),
        relevance_score=0.8,
        topics=[Topic.LLM],
        importance_score=0.7,
    )


def create_paper_item() -> ProcessedItem:
    """Create a processed research paper."""
    return ProcessedItem(
        item=ResearchPaper(
            id="p1",
            arxiv_id="2609.1",
            title="On scaling",
            authors=["Alice Smith", "Bob Jones"],
            abstract="An abstract.",
            url="https://arxiv.org/abs/2609.1",
            published_at="2026-09-15T00:00:00Z",
            updated_at="2026-09-15T00:00:00Z",
            categories=["cs.LG"],
            summary="They scaled things.",
        ),
        relevance_score=0.9,
        topics=[Topic.MACHINE_LEARNING],
        importance_score=0.9,
    )


def test_render_includes_brief_text() -> None:
    html = BriefRenderer().render(
        create_brief(),
        [create_article_item()],
    )

    assert "Good morning." in html
    assert "Agents were the theme." in html
    assert "September 16, 2026" in html


def test_render_separates_news_and_research() -> None:
    html = BriefRenderer().render(
        create_brief(),
        [create_article_item(), create_paper_item()],
    )

    assert "In the news" in html
    assert "From arXiv" in html
    assert "A model shipped" in html
    assert "On scaling" in html


def test_empty_sections_are_omitted() -> None:
    html = BriefRenderer().render(
        create_brief(),
        [create_article_item()],
    )

    assert "In the news" in html
    assert "From arXiv" not in html


def test_item_text_is_escaped() -> None:
    html = BriefRenderer().render(
        create_brief(),
        [
            create_article_item(
                title="<script>alert(1)</script>",
                summary="5 > 3 & rising",
            ),
        ],
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "5 &gt; 3 &amp; rising" in html


def test_missing_summary_is_skipped() -> None:
    html = BriefRenderer().render(
        create_brief(),
        [create_article_item(summary=None, why=None)],
    )

    assert "A model shipped" in html
    assert "Why it matters" not in html


def test_subject_is_the_brief_title() -> None:
    brief = create_brief()

    assert (
        BriefRenderer().render_subject(brief) == brief.title
    )
