from unittest.mock import patch

from backend.collectors.rss.collector import (
    RSSCollectionError,
    RSSCollector,
)
from backend.models import Source, SourceType


def create_source() -> Source:
    return Source(
        name="Example",
        feed_url="https://example.com/feed.xml",
        source_type=SourceType.NEWS,
    )


def test_collect_returns_raw_entries() -> None:
    fake_feed = {
        "bozo": False,
        "entries": [
            {
                "title": "First article",
                "link": "https://example.com/first",
            },
            {
                "title": "Second article",
                "link": "https://example.com/second",
            },
        ],
    }

    with patch(
        "backend.collectors.rss.collector.feedparser.parse",
        return_value=fake_feed,
    ):
        collector = RSSCollector()

        entries = collector.collect(create_source())

    assert len(entries) == 2
    assert entries[0]["title"] == "First article"
    assert entries[1]["title"] == "Second article"
    
    
def test_collect_raises_when_feed_is_invalid() -> None:
    fake_feed = {
        "bozo": True,
        "entries": [],
    }

    with patch(
        "backend.collectors.rss.collector.feedparser.parse",
        return_value=fake_feed,
    ):
        collector = RSSCollector()

        try:
            collector.collect(create_source())
        except RSSCollectionError:
            pass
        else:
            raise AssertionError(
                "Expected RSSCollectionError to be raised"
            )