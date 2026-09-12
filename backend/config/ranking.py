"""Configuration for content importance ranking."""

from pydantic import BaseModel, ConfigDict, Field


class RankingConfig(BaseModel):
    """Configuration for deterministic importance ranking."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    recency_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
    )

    relevance_weight: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
    )

    source_quality_weight: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
    )

    significance_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
    )

    recency_half_life_hours: float = Field(
        default=48.0,
        gt=0.0,
    )


DEFAULT_RANKING_CONFIG = RankingConfig()