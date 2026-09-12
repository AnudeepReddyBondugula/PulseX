"""Tests for content processing orchestration."""

from unittest.mock import Mock

from backend.models.article import Article
from backend.models.topic import Topic
from backend.processors.deduplication.processor import (
    DeduplicationResult,
)
from backend.processors.ranking.processor import (
    RankingResult,
)
from backend.processors.relevance.processor import (
    RelevanceResult,
)
from backend.services.content_processing import (
    ContentProcessingService,
)


def create_article(
    article_id: str,
    title: str,
) -> Article:
    """Create a test article."""
    return Article(
        id=article_id,
        title=title,
        source="Test Source",
        source_url="https://example.com",
        url=f"https://example.com/{article_id}",
        published_at="2026-01-01T00:00:00Z",
        fetched_at="2026-01-01T01:00:00Z",
        content_hash=f"hash-{article_id}",
    )


def test_process_runs_pipeline_in_order() -> None:
    article = create_article(
        "1",
        "New LLM model",
    )

    deduplicator = Mock()
    relevance = Mock()
    topics = Mock()
    ranking = Mock()

    deduplicator.deduplicate.return_value = (
        DeduplicationResult(
            unique=[article],
            duplicates=[],
        )
    )

    relevance_result = RelevanceResult(
        item=article,
        score=0.8,
        is_relevant=True,
    )

    relevance.filter.return_value = [
        relevance_result,
    ]

    topics.extract.return_value = [
        Topic.LLM,
    ]

    ranking_result = RankingResult(
        item=article,
        score=0.9,
    )

    ranking.rank.return_value = [
        ranking_result,
    ]

    service = ContentProcessingService(
        deduplicator=deduplicator,
        relevance_processor=relevance,
        topic_extractor=topics,
        ranking_processor=ranking,
    )

    result = service.process([article])

    assert len(result.items) == 1

    processed = result.items[0]

    assert processed.item == article
    assert processed.relevance_score == 0.8
    assert processed.topics == [Topic.LLM]
    assert processed.importance_score == 0.9

    deduplicator.deduplicate.assert_called_once_with(
        [article],
    )

    relevance.filter.assert_called_once_with(
        [article],
    )

    topics.extract.assert_called_once()

    ranking.rank.assert_called_once_with(
        [article],
        relevance_scores={
            "1": 0.8,
        },
        now=None,
    )


def test_process_excludes_irrelevant_content() -> None:
    article = create_article(
        "1",
        "Sports news",
    )

    deduplicator = Mock()
    relevance = Mock()
    topics = Mock()
    ranking = Mock()

    deduplicator.deduplicate.return_value = (
        DeduplicationResult(
            unique=[article],
            duplicates=[],
        )
    )

    relevance_result = RelevanceResult(
        item=article,
        score=0.0,
        is_relevant=False,
    )

    relevance.filter.return_value = [
        relevance_result,
    ]

    service = ContentProcessingService(
        deduplicator=deduplicator,
        relevance_processor=relevance,
        topic_extractor=topics,
        ranking_processor=ranking,
    )

    result = service.process([article])

    assert result.items == []
    assert result.irrelevant == [
        relevance_result,
    ]

    topics.extract.assert_not_called()
    ranking.rank.assert_not_called()


def test_process_preserves_duplicates() -> None:
    first = create_article(
        "1",
        "AI article",
    )

    duplicate = create_article(
        "2",
        "AI article",
    )

    deduplicator = Mock()
    relevance = Mock()
    topics = Mock()
    ranking = Mock()

    deduplicator.deduplicate.return_value = (
        DeduplicationResult(
            unique=[first],
            duplicates=[duplicate],
        )
    )

    relevance_result = RelevanceResult(
        item=first,
        score=0.8,
        is_relevant=True,
    )

    relevance.filter.return_value = [
        relevance_result,
    ]

    topics.extract.return_value = [
        Topic.LLM,
    ]

    ranking.rank.return_value = [
        RankingResult(
            item=first,
            score=0.9,
        ),
    ]

    service = ContentProcessingService(
        deduplicator=deduplicator,
        relevance_processor=relevance,
        topic_extractor=topics,
        ranking_processor=ranking,
    )

    result = service.process(
        [first, duplicate],
    )

    assert result.duplicates == [
        duplicate,
    ]