"""Configuration for arXiv ingestion."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from backend.models.topic import Topic


ARXIV_DATE_FORMAT = "%Y%m%d%H%M"


class ArxivSortBy(StrEnum):
    """Supported arXiv result sorting fields."""

    RELEVANCE = "relevance"
    LAST_UPDATED = "lastUpdatedDate"
    SUBMITTED = "submittedDate"


class ArxivSortOrder(StrEnum):
    """Supported arXiv result sorting orders."""

    ASCENDING = "ascending"
    DESCENDING = "descending"


class ArxivQueryConfig(BaseModel):
    """Configuration for a single arXiv API query."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    query: str = Field(min_length=1)
    max_results: int = Field(
        default=20,
        ge=1,
        le=100,
    )
    sort_by: ArxivSortBy = ArxivSortBy.SUBMITTED
    sort_order: ArxivSortOrder = ArxivSortOrder.DESCENDING
    lookback_hours: int | None = Field(
        default=None,
        gt=0,
    )

    def build_search_query(
        self,
        now: datetime | None = None,
    ) -> str:
        """Return the query to send to the arXiv API.

        Sorting by submission date returns the newest papers, but
        without a date range it returns them whatever their age, so
        consecutive daily runs overlap heavily. When lookback_hours
        is set the query is restricted to that window instead.
        """
        if self.lookback_hours is None:
            return self.query

        end = now or datetime.now(UTC)
        start = end - timedelta(hours=self.lookback_hours)

        return (
            f"({self.query}) AND submittedDate:"
            f"[{start.strftime(ARXIV_DATE_FORMAT)}"
            f" TO {end.strftime(ARXIV_DATE_FORMAT)}]"
        )


# arXiv categories backing each PulseX topic. Papers are fetched by
# category, then the topic extractor labels them from their text, so
# these only need to be broad enough to surface relevant work.
TOPIC_ARXIV_CATEGORIES: dict[Topic, tuple[str, ...]] = {
    Topic.LLM: ("cs.CL",),
    Topic.GENERATIVE_AI: ("cs.LG",),
    Topic.AI_AGENTS: ("cs.MA",),
    Topic.MACHINE_LEARNING: ("cs.LG", "stat.ML"),
    Topic.DEEP_LEARNING: ("cs.NE",),
    Topic.COMPUTER_VISION: ("cs.CV",),
    Topic.NLP: ("cs.CL",),
    Topic.MULTIMODAL_AI: ("cs.CV", "cs.CL"),
    Topic.ROBOTICS: ("cs.RO",),
    Topic.AI_SAFETY: ("cs.CY",),
    Topic.AI_INFRASTRUCTURE: ("cs.DC",),
    Topic.AI_RESEARCH: ("cs.AI",),
    Topic.AI_HARDWARE: ("cs.AR",),
}


ARXIV_CATEGORIES: tuple[str, ...] = tuple(
    sorted(
        {
            category
            for categories in (
                TOPIC_ARXIV_CATEGORIES.values()
            )
            for category in categories
        }
    )
)


ARXIV_LOOKBACK_HOURS = 24

ARXIV_MAX_RESULTS = 100


def build_category_query(
    categories: tuple[str, ...] = ARXIV_CATEGORIES,
) -> str:
    """Combine categories into one arXiv search expression."""
    return " OR ".join(
        f"cat:{category}" for category in categories
    )


# One combined query rather than one per category: arXiv asks
# clients to space out requests, and a single OR expression
# returns the same papers in one call.
ARXIV_QUERIES: tuple[ArxivQueryConfig, ...] = (
    ArxivQueryConfig(
        query=build_category_query(),
        max_results=ARXIV_MAX_RESULTS,
        lookback_hours=ARXIV_LOOKBACK_HOURS,
    ),
)
