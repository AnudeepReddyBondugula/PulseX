"""RSS feed collection."""

from typing import Any

import feedparser

from backend.models import Source


class RSSCollectionError(Exception):
    """Raised when an RSS feed cannot be collected."""


class RSSCollector:
    """Fetch and parse entries from an RSS or Atom source."""

    def collect(self, source: Source) -> list[dict[str, Any]]:
        """Collect raw entries from a configured RSS source."""
        feed = feedparser.parse(str(source.feed_url))

        entries = feed.get("entries", [])
        bozo = feed.get("bozo", False)

        if bozo and not entries:
            raise RSSCollectionError(
                f"Failed to parse RSS feed: {source.name}"
            )

        return [dict(entry) for entry in entries]