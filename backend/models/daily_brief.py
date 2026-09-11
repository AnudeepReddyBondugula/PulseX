from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DailyBrief(BaseModel):
    """The curated PulseX briefing for a single day."""

    model_config = ConfigDict(
        extra="forbid",
    )

    id: str = Field(min_length=1)

    date: date

    title: str = Field(min_length=1)

    introduction: str = Field(min_length=1)

    article_ids: list[str] = Field(default_factory=list)

    paper_ids: list[str] = Field(default_factory=list)

    generated_at: datetime

    summary: str = Field(min_length=1)