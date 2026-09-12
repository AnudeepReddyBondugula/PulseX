"""RSS feed collection."""

import logging
from typing import Any

import feedparser

from backend.models import Source


logger = logging.getLogger(__name__)


class RSSCollectionError(Exception):
    """Raised when an RSS feed cannot be collected."""


class RSSCollector:
    """Fetch and parse entries from an RSS or Atom source."""

    def collect(self, source: Source) -> list[dict[str, Any]]:
        """Collect raw entries from a configured RSS source."""
        if not source.enabled:
            logger.info(
                "Skipping disabled RSS source: %s",
                source.name,
            )
            return []

        logger.info(
            "Collecting RSS feed: %s",
            source.name,
        )

        try:
            feed = feedparser.parse(str(source.feed_url))
        except Exception as exc:
            logger.exception(
                "Failed to collect RSS feed: %s",
                source.name,
            )

            raise RSSCollectionError(
                f"Failed to collect RSS feed: {source.name}"
            ) from exc

        entries = feed.get("entries", [])
        bozo = feed.get("bozo", False)

        if bozo and not entries:
            logger.error(
                "Failed to parse RSS feed: %s",
                source.name,
            )

            raise RSSCollectionError(
                f"Failed to parse RSS feed: {source.name}"
            )

        logger.info(
            "RSS feed collected: %s entries=%d",
            source.name,
            len(entries),
        )

        return [dict(entry) for entry in entries]