"""Configuration for content relevance scoring."""

from pydantic import BaseModel, ConfigDict, Field


class RelevanceConfig(BaseModel):
    """Configuration for deterministic relevance scoring."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    keywords: tuple[str, ...] = Field(
        min_length=1,
    )

    threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
    )

    title_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
    )

    body_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
    )


DEFAULT_RELEVANCE_CONFIG = RelevanceConfig(
    keywords=(
        "artificial intelligence",
        "ai",
        "llm",
        "large language model",
        "generative ai",
        "ai agent",
        "ai agents",
        "machine learning",
        "deep learning",
        "computer vision",
        "natural language processing",
        "nlp",
        "multimodal",
        "robotics",
        "ai safety",
        "ai infrastructure",
        "ai research",
        "ai hardware",
        "transformer",
        "inference",
        "fine-tuning",
        "reinforcement learning",
        "reasoning",
    ),
)