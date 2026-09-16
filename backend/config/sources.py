"""Configuration for PulseX content sources."""

from backend.models import Source, SourceType


RSS_SOURCES: tuple[Source, ...] = (
    Source(
        name="OpenAI",
        feed_url="https://openai.com/news/rss.xml",
        source_type=SourceType.NEWS,
    ),
)