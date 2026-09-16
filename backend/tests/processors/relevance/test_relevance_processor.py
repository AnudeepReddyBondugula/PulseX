"""Tests for relevance scoring."""

from backend.config.relevance import RelevanceConfig
from backend.models.article import Article
from backend.processors.relevance.processor import (
    RelevanceProcessor,
)


def create_article(
    *,
    title: str,
    description: str | None = None,
    content: str | None = None,
) -> Article:
    """Create a minimal test article."""
    return Article(
        id="test-id",
        title=title,
        source="Test Source",
        source_url="https://example.com",
        url="https://example.com/article",
        published_at="2026-01-01T00:00:00Z",
        fetched_at="2026-01-01T01:00:00Z",
        description=description,
        content=content,
        content_hash="test-hash",
    )


def test_relevant_title_produces_positive_score() -> None:
    article = create_article(
        title="New LLM architecture improves reasoning",
    )

    processor = RelevanceProcessor()

    result = processor.evaluate(article)

    assert result.score > 0.0
    assert result.is_relevant is True


def test_irrelevant_article_produces_zero_score() -> None:
    article = create_article(
        title="New football stadium opens",
        description="A new sports stadium was announced.",
    )

    processor = RelevanceProcessor()

    result = processor.evaluate(article)

    assert result.score == 0.0
    assert result.is_relevant is False


def test_title_has_higher_weight_than_body() -> None:
    title_match = create_article(
        title="New LLM architecture",
        content="A general technology announcement.",
    )

    body_match = create_article(
        title="New technology announcement",
        content="Researchers developed a new LLM.",
    )

    processor = RelevanceProcessor()

    title_result = processor.evaluate(title_match)
    body_result = processor.evaluate(body_match)

    assert title_result.score > body_result.score


def test_multiple_keywords_increase_score() -> None:
    one_keyword = create_article(
        title="New LLM system",
    )

    three_keywords = create_article(
        title="New LLM transformer for AI reasoning",
    )

    processor = RelevanceProcessor()

    one_result = processor.evaluate(one_keyword)
    three_result = processor.evaluate(three_keywords)

    assert three_result.score > one_result.score


def test_score_is_capped_at_one() -> None:
    article = create_article(
        title=(
            "AI LLM transformer machine learning "
            "deep learning computer vision NLP "
            "robotics multimodal reasoning"
        ),
    )

    processor = RelevanceProcessor()

    result = processor.evaluate(article)

    assert result.score <= 1.0


def test_keyword_matching_is_case_insensitive() -> None:
    article = create_article(
        title="NEW LLM ARCHITECTURE",
    )

    processor = RelevanceProcessor()

    result = processor.evaluate(article)

    assert result.score > 0.0


def test_keyword_matching_handles_extra_whitespace() -> None:
    article = create_article(
        title="New    LLM   architecture",
    )

    processor = RelevanceProcessor()

    result = processor.evaluate(article)

    assert result.score > 0.0


def test_short_ai_keyword_does_not_match_inside_words() -> None:
    article = create_article(
        title="The company said it will build a railway.",
    )

    processor = RelevanceProcessor()

    result = processor.evaluate(article)

    assert result.score == 0.0


def test_threshold_controls_relevance() -> None:
    config = RelevanceConfig(
        keywords=("llm",),
        threshold=0.9,
    )

    article = create_article(
        title="New LLM architecture",
    )

    processor = RelevanceProcessor(config)

    result = processor.evaluate(article)

    assert result.score < 0.9
    assert result.is_relevant is False


def test_filter_returns_results_for_all_items() -> None:
    relevant = create_article(
        title="New LLM architecture",
    )

    irrelevant = create_article(
        title="New football stadium",
    )

    processor = RelevanceProcessor()

    results = processor.filter(
        [relevant, irrelevant],
    )

    assert len(results) == 2
    assert results[0].item == relevant
    assert results[1].item == irrelevant


def test_filter_relevant_returns_only_relevant_items() -> None:
    relevant = create_article(
        title="New LLM (large language model) architecture",
    )

    irrelevant = create_article(
        title="New football stadium",
    )

    processor = RelevanceProcessor()

    result = processor.filter_relevant(
        [relevant, irrelevant],
    )

    assert result == [relevant]