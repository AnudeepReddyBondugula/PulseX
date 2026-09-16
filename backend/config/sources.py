"""Configuration for PulseX content sources.

Feed URLs are verified on each run rather than at import time.
CollectionService records a failure per source and continues, so a
feed that moves or breaks costs only its own items, not the run.
"""

from backend.models import Source, SourceType


RSS_SOURCES: tuple[Source, ...] = (
    Source(
        name="OpenAI",
        feed_url="https://openai.com/news/rss.xml",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="Anthropic",
        feed_url="https://www.anthropic.com/news/rss.xml",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="Google DeepMind",
        feed_url="https://deepmind.google/blog/rss.xml",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="Google AI",
        feed_url="https://blog.google/technology/ai/rss/",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="Meta AI",
        feed_url="https://ai.meta.com/blog/rss/",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="Microsoft Research",
        feed_url="https://www.microsoft.com/en-us/research/feed/",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="Hugging Face",
        feed_url="https://huggingface.co/blog/feed.xml",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="TechCrunch AI",
        feed_url=(
            "https://techcrunch.com/category/"
            "artificial-intelligence/feed/"
        ),
        source_type=SourceType.NEWS,
    ),
    Source(
        name="MIT Technology Review AI",
        feed_url=(
            "https://www.technologyreview.com/topic/"
            "artificial-intelligence/feed/"
        ),
        source_type=SourceType.NEWS,
    ),
    Source(
        name="Ars Technica AI",
        feed_url="https://arstechnica.com/ai/feed/",
        source_type=SourceType.NEWS,
    ),
    Source(
        name="The Verge AI",
        feed_url=(
            "https://www.theverge.com/rss/"
            "ai-artificial-intelligence/index.xml"
        ),
        source_type=SourceType.NEWS,
    ),
)
