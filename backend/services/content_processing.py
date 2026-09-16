"""Content processing orchestration."""

from dataclasses import dataclass

from backend.models import Article, ResearchPaper, Topic

from datetime import datetime

from backend.processors.deduplication.processor import (
    DeduplicationResult,
    Deduplicator,
)
from backend.processors.ranking.processor import (
    RankingProcessor,
    RankingResult,
)
from backend.processors.relevance.processor import (
    RelevanceProcessor,
    RelevanceResult,
)
from backend.processors.topics.processor import TopicExtractor


ContentItem = Article | ResearchPaper


@dataclass(frozen=True)
class ProcessedItem:
    """Content item enriched with processing metadata."""

    item: ContentItem
    relevance_score: float
    topics: list[Topic]
    importance_score: float
    
    
@dataclass(frozen=True)
class ProcessedContent:
    """Final output of deterministic content processing."""

    items: list[ProcessedItem]
    duplicates: list[ContentItem]
    irrelevant: list[RelevanceResult]
    
    
class ContentProcessingService:
    """Orchestrate deterministic content processing."""

    def __init__(
        self,
        deduplicator: Deduplicator,
        relevance_processor: RelevanceProcessor,
        topic_extractor: TopicExtractor,
        ranking_processor: RankingProcessor,
    ) -> None:
        self._deduplicator = deduplicator
        self._relevance_processor = relevance_processor
        self._topic_extractor = topic_extractor
        self._ranking_processor = ranking_processor

    def process(
        self,
        items: list[ContentItem],
        *,
        now: datetime | None = None,
    ) -> ProcessedContent:
        """Process content through all deterministic stages."""
        deduplication = self._deduplicator.deduplicate(
            items,
        )

        relevance_results = (
            self._relevance_processor.filter(
                deduplication.unique,
            )
        )

        relevant_results = [
            result
            for result in relevance_results
            if result.is_relevant
        ]

        relevance_scores = {
            result.item.id: result.score
            for result in relevant_results
        }

        topics_by_id = {
            result.item.id: self._extract_topics(
                result.item,
            )
            for result in relevant_results
        }

        ranking_results = (
            self._ranking_processor.rank(
                [
                    result.item
                    for result in relevant_results
                ],
                relevance_scores=relevance_scores,
                now=now,
            )
            if relevant_results
            else []
        )

        processed_items = [
            ProcessedItem(
                item=result.item,
                relevance_score=relevance_scores[
                    result.item.id
                ],
                topics=topics_by_id[result.item.id],
                importance_score=result.score,
            )
            for result in ranking_results
        ]

        irrelevant = [
            result
            for result in relevance_results
            if not result.is_relevant
        ]

        return ProcessedContent(
            items=processed_items,
            duplicates=deduplication.duplicates,
            irrelevant=irrelevant,
        )

    def _extract_topics(
        self,
        item: ContentItem,
    ) -> list[Topic]:
        """Extract topics from a content item."""
        text = self._build_topic_text(item)

        return self._topic_extractor.extract(text)

    @staticmethod
    def _build_topic_text(
        item: ContentItem,
    ) -> str:
        """Build searchable text for topic extraction."""
        if isinstance(item, Article):
            return " ".join(
                part
                for part in (
                    item.title,
                    item.description,
                    item.content,
                    item.summary,
                )
                if part
            )

        return " ".join(
            part
            for part in (
                item.title,
                item.abstract,
                item.summary,
            )
            if part
        )