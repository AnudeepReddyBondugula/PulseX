from backend.config.sources import RSS_SOURCES
from backend.models import Source, SourceType


def test_rss_sources_are_configured() -> None:
    assert RSS_SOURCES
    assert all(isinstance(source, Source) for source in RSS_SOURCES)


def test_rss_sources_are_immutable() -> None:
    assert isinstance(RSS_SOURCES, tuple)


def test_rss_sources_have_required_fields() -> None:
    for source in RSS_SOURCES:
        assert source.name
        assert source.feed_url
        assert source.source_type in (
            SourceType.NEWS,
            SourceType.RESEARCH,
        )
        assert source.enabled is True