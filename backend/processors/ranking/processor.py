"""Deterministic content importance ranking."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.config.ranking import (
    DEFAULT_RANKING_CONFIG,
    RankingConfig,
)
from backend.config.source_quality import (
    SOURCE_QUALITY_SCORES,
)
from backend.models.article import Article
from backend.models.research_paper import ResearchPaper


ContentItem = Article | ResearchPaper

ARXIV_SOURCE_NAME = "arXiv"


def _item_source(item: ContentItem) -> str:
    """Return the source name to score an item against.

    Only articles carry a source name; every paper comes from
    arXiv, which the quality table already scores.
    """
    if isinstance(item, ResearchPaper):
        return ARXIV_SOURCE_NAME

    return item.source


@dataclass(frozen=True)
class RankingResult:
    """A content item together with its importance score."""

    item: ContentItem
    score: float


class RankingProcessor:
    """Calculate deterministic importance scores."""

    def __init__(
        self,
        config: RankingConfig = DEFAULT_RANKING_CONFIG,
        source_quality: dict[str, float] = SOURCE_QUALITY_SCORES,
    ) -> None:
        self._config = config
        self._source_quality = source_quality

    def score(
        self,
        item: ContentItem,
        *,
        relevance_score: float,
        now: datetime | None = None,
    ) -> RankingResult:
        """Calculate an importance score for one item."""
        current_time = now or datetime.now(UTC)

        recency_score = self._calculate_recency_score(
            item.published_at,
            current_time,
        )

        source_score = self._calculate_source_quality(
            _item_source(item),
        )

        significance_score = self._calculate_significance_score(
            item,
        )

        normalized_relevance = min(
            max(relevance_score, 0.0),
            1.0,
        )

        final_score = (
            recency_score * self._config.recency_weight
            + normalized_relevance
            * self._config.relevance_weight
            + source_score
            * self._config.source_quality_weight
            + significance_score
            * self._config.significance_weight
        )

        final_score = min(
            max(final_score, 0.0),
            1.0,
        )

        return RankingResult(
            item=item,
            score=final_score,
        )

    def rank(
        self,
        items: list[ContentItem],
        *,
        relevance_scores: dict[str, float],
        now: datetime | None = None,
    ) -> list[RankingResult]:
        """Score and sort content by importance."""
        results = [
            self.score(
                item,
                relevance_score=relevance_scores.get(
                    item.id,
                    0.0,
                ),
                now=now,
            )
            for item in items
        ]

        return sorted(
            results,
            key=lambda result: result.score,
            reverse=True,
        )

    def _calculate_recency_score(
        self,
        published_at: datetime,
        now: datetime,
    ) -> float:
        """Calculate recency using exponential decay."""
        published_at = self._ensure_utc(published_at)
        now = self._ensure_utc(now)

        age_seconds = max(
            (now - published_at).total_seconds(),
            0.0,
        )

        age_hours = age_seconds / 3600.0

        half_life = (
            self._config.recency_half_life_hours
        )

        return math.pow(
            0.5,
            age_hours / half_life,
        )

    @staticmethod
    def _ensure_utc(
        value: datetime,
    ) -> datetime:
        """Return a timezone-aware UTC datetime."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    def _calculate_source_quality(
        self,
        source: str,
    ) -> float:
        """Return configured source quality."""
        score = self._source_quality.get(
            source,
            0.5,
        )

        return min(
            max(score, 0.0),
            1.0,
        )

    @staticmethod
    def _calculate_significance_score(
        item: ContentItem,
    ) -> float:
        """Calculate deterministic technical significance."""
        score = 0.0

        title = item.title.lower()

        high_impact_terms = (
            "new model",
            "new architecture",
            "breakthrough",
            "state-of-the-art",
            "state of the art",
            "benchmark",
            "release",
            "launch",
            "open source",
            "open-source",
            "research",
        )

        matched_terms = sum(
            term in title
            for term in high_impact_terms
        )

        score += min(
            matched_terms * 0.2,
            0.6,
        )

        if isinstance(item, ResearchPaper):
            score += 0.2

        return min(score, 1.0)