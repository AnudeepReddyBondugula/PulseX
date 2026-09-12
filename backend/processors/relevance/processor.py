"""Deterministic AI relevance scoring."""

import re
from dataclasses import dataclass

from backend.config.relevance import (
    DEFAULT_RELEVANCE_CONFIG,
    RelevanceConfig,
)
from backend.models.article import Article
from backend.models.research_paper import ResearchPaper


ContentItem = Article | ResearchPaper


@dataclass(frozen=True)
class RelevanceResult:
    """Result of relevance evaluation."""

    item: ContentItem
    score: float
    is_relevant: bool


class RelevanceProcessor:
    """Calculate deterministic AI relevance scores."""

    def __init__(
        self,
        config: RelevanceConfig = DEFAULT_RELEVANCE_CONFIG,
    ) -> None:
        self._config = config

    def evaluate(
        self,
        item: ContentItem,
    ) -> RelevanceResult:
        """Evaluate the relevance of one content item."""
        title_score = self._calculate_text_score(
            item.title,
        )

        body = self._get_body_text(item)

        body_score = self._calculate_text_score(body)

        score = (
            title_score * self._config.title_weight
            + body_score * self._config.body_weight
        )

        score = min(max(score, 0.0), 1.0)

        return RelevanceResult(
            item=item,
            score=score,
            is_relevant=score >= self._config.threshold,
        )

    def filter(
        self,
        items: list[ContentItem],
    ) -> list[RelevanceResult]:
        """Return relevance results for all content items."""
        return [
            self.evaluate(item)
            for item in items
        ]

    def filter_relevant(
        self,
        items: list[ContentItem],
    ) -> list[ContentItem]:
        """Return only relevant content items."""
        return [
            result.item
            for result in self.filter(items)
            if result.is_relevant
        ]

    def _get_body_text(
        self,
        item: ContentItem,
    ) -> str:
        """Return searchable body text for an item."""
        if isinstance(item, Article):
            return " ".join(
                part
                for part in (
                    item.description,
                    item.content,
                    item.summary,
                )
                if part
            )

        return " ".join(
            part
            for part in (
                item.abstract,
                item.summary,
            )
            if part
        )

    def _calculate_text_score(
        self,
        text: str,
    ) -> float:
        """Calculate keyword coverage score for text."""
        normalized_text = self._normalize_text(text)

        if not normalized_text:
            return 0.0

        matched_keywords = {
            keyword
            for keyword in self._config.keywords
            if self._contains_keyword(
                normalized_text,
                keyword,
            )
        }

        if not matched_keywords:
            return 0.0

        return min(
            len(matched_keywords) / 5.0,
            1.0,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text before keyword matching."""
        text = text.lower()
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        """Check whether a keyword occurs as a phrase/word."""
        normalized_keyword = keyword.lower().strip()

        if not normalized_keyword:
            return False

        pattern = rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)"

        return re.search(
            pattern,
            text,
        ) is not None