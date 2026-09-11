from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .topic import Topic


class Article(BaseModel):
    """Normalized AI news article."""

    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(min_length=1)

    title: str = Field(min_length=1)

    source: str = Field(min_length=1)
    source_url: HttpUrl
    url: HttpUrl

    author: str | None = None

    published_at: datetime
    fetched_at: datetime

    description: str | None = None
    content: str | None = None
    image_url: HttpUrl | None = None

    topics: list[Topic] = Field(default_factory=list)

    importance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    summary: str | None = None
    why_it_matters: str | None = None

    content_hash: str = Field(min_length=1)