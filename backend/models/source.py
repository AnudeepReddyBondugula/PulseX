from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceType(StrEnum):
    """Types of content sources supported by PulseX."""

    NEWS = "news"
    RESEARCH = "research"


class Source(BaseModel):
    """Configuration for a trusted PulseX content source."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str = Field(min_length=1)
    feed_url: HttpUrl
    source_type: SourceType
    enabled: bool = True