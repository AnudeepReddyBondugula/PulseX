"""Tests for importance ranking."""

from datetime import UTC, datetime, timedelta

from backend.config.ranking import RankingConfig
from backend.models.article import Article
from backend.processors.ranking.processor import RankingProcessor


NOW = datetime(
    2026,
    1,
    10,
    12,
    0,
    tzinfo=UTC,
)


def create_article(
    *,
    article_id: str,
    title: str = "AI news",
    source: str = "Test Source",
    published_at: datetime = NOW,
) -> Article:
    """Create a minimal test article."""
    return Article(
        id=article_id,
        title=title,
        source=source,
        source_url="https://example.com",
        url=f"https://example.com/{article_id}",
        published_at=published_at,
        fetched_at=NOW,
        content_hash=f"hash-{article_id}",
    )


def test_score_is_between_zero_and_one() -> None:
    article = create_article(
        article_id="1",
        title="New AI model release",
    )

    processor = RankingProcessor()

    result = processor.score(
        article,
        relevance_score=0.8,
        now=NOW,
    )

    assert 0.0 <= result.score <= 1.0


def test_newer_content_has_higher_recency_score() -> None:
    recent = create_article(
        article_id="recent",
        published_at=NOW,
    )

    old = create_article(
        article_id="old",
        published_at=NOW - timedelta(days=4),
    )

    processor = RankingProcessor()

    recent_result = processor.score(
        recent,
        relevance_score=0.5,
        now=NOW,
    )

    old_result = processor.score(
        old,
        relevance_score=0.5,
        now=NOW,
    )

    assert recent_result.score > old_result.score


def test_higher_relevance_increases_score() -> None:
    article = create_article(
        article_id="1",
    )

    processor = RankingProcessor()

    low = processor.score(
        article,
        relevance_score=0.2,
        now=NOW,
    )

    high = processor.score(
        article,
        relevance_score=0.9,
        now=NOW,
    )

    assert high.score > low.score


def test_higher_source_quality_increases_score() -> None:
    article = create_article(
        article_id="1",
        source="High Quality",
    )

    processor = RankingProcessor(
        source_quality={
            "High Quality": 1.0,
            "Low Quality": 0.2,
        },
    )

    high_quality = processor.score(
        article,
        relevance_score=0.5,
        now=NOW,
    )

    low_quality_article = create_article(
        article_id="2",
        source="Low Quality",
    )

    low_quality = processor.score(
        low_quality_article,
        relevance_score=0.5,
        now=NOW,
    )

    assert high_quality.score > low_quality.score


def test_unknown_source_uses_fallback_score() -> None:
    article = create_article(
        article_id="1",
        source="Unknown Source",
    )

    processor = RankingProcessor(
        source_quality={},
    )

    result = processor.score(
        article,
        relevance_score=0.5,
        now=NOW,
    )

    assert 0.0 <= result.score <= 1.0


def test_significance_terms_increase_score() -> None:
    ordinary = create_article(
        article_id="ordinary",
        title="AI update",
    )

    significant = create_article(
        article_id="significant",
        title=(
            "New AI model achieves "
            "state-of-the-art benchmark results"
        ),
    )

    processor = RankingProcessor()

    ordinary_result = processor.score(
        ordinary,
        relevance_score=0.5,
        now=NOW,
    )

    significant_result = processor.score(
        significant,
        relevance_score=0.5,
        now=NOW,
    )

    assert significant_result.score > ordinary_result.score


def test_negative_relevance_is_clamped() -> None:
    article = create_article(
        article_id="1",
    )

    processor = RankingProcessor()

    result = processor.score(
        article,
        relevance_score=-10.0,
        now=NOW,
    )

    assert 0.0 <= result.score <= 1.0


def test_relevance_above_one_is_clamped() -> None:
    article = create_article(
        article_id="1",
    )

    processor = RankingProcessor()

    result = processor.score(
        article,
        relevance_score=10.0,
        now=NOW,
    )

    assert 0.0 <= result.score <= 1.0


def test_rank_returns_items_in_descending_order() -> None:
    low = create_article(
        article_id="low",
        title="AI update",
    )

    high = create_article(
        article_id="high",
        title=(
            "New AI model achieves "
            "state-of-the-art benchmark results"
        ),
    )

    processor = RankingProcessor()

    results = processor.rank(
        [low, high],
        relevance_scores={
            "low": 0.2,
            "high": 0.9,
        },
        now=NOW,
    )

    assert [result.item.id for result in results] == [
        "high",
        "low",
    ]


def test_missing_relevance_score_defaults_to_zero() -> None:
    article = create_article(
        article_id="1",
    )

    processor = RankingProcessor()

    result = processor.rank(
        [article],
        relevance_scores={},
        now=NOW,
    )

    assert result[0].score >= 0.0


def test_recency_half_life_is_respected() -> None:
    article = create_article(
        article_id="1",
        published_at=NOW - timedelta(hours=48),
    )

    config = RankingConfig(
        recency_weight=1.0,
        relevance_weight=0.0,
        source_quality_weight=0.0,
        significance_weight=0.0,
        recency_half_life_hours=48.0,
    )

    processor = RankingProcessor(config)

    result = processor.score(
        article,
        relevance_score=0.0,
        now=NOW,
    )

    assert result.score == 0.5