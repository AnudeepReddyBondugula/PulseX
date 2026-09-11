from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .topic import Topic


class ResearchPaper(BaseModel):
    """Normalized AI research paper."""

    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(min_length=1)

    arxiv_id: str = Field(min_length=1)

    title: str = Field(min_length=1)

    authors: list[str] = Field(default_factory=list)

    abstract: str = Field(min_length=1)

    url: HttpUrl

    published_at: datetime
    updated_at: datetime

    categories: list[str] = Field(default_factory=list)

    topics: list[Topic] = Field(default_factory=list)

    importance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    summary: str | None = None
    why_it_matters: str | None = None