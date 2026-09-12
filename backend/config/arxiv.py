"""Configuration for arXiv ingestion."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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


ARXIV_QUERIES: tuple[ArxivQueryConfig, ...] = (
    ArxivQueryConfig(
        query="cat:cs.AI",
        max_results=20,
    ),
    ArxivQueryConfig(
        query="cat:cs.LG",
        max_results=20,
    ),
)