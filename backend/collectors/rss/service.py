"""RSS ingestion orchestration."""

import logging

from pydantic import ValidationError

from backend.collectors.rss.collector import (
    RSSCollectionError,
    RSSCollector,
)
from backend.collectors.rss.normalizer import (
    RSSNormalizationError,
    RSSNormalizer,
)
from backend.models import Article, Source


logger = logging.getLogger(__name__)


class RSSIngestionError(Exception):
    """Raised when RSS ingestion fails."""


class RSSIngestionService:
    """Orchestrate RSS collection and normalization."""

    def __init__(
        self,
        collector: RSSCollector,
        normalizer: RSSNormalizer,
    ) -> None:
        self._collector = collector
        self._normalizer = normalizer

    def ingest(self, source: Source) -> list[Article]:
        """Collect and normalize articles for one RSS source."""
        logger.info(
            "Starting RSS ingestion: source=%s",
            source.name,
        )

        try:
            entries = self._collector.collect(source)
        except RSSCollectionError as exc:
            logger.exception(
                "RSS ingestion failed: source=%s",
                source.name,
            )

            raise RSSIngestionError(
                f"Failed to ingest RSS source: {source.name}"
            ) from exc

        articles: list[Article] = []

        for entry in entries:
            article = self._normalize_entry(entry, source)

            if article is not None:
                articles.append(article)

        logger.info(
            "Completed RSS ingestion: source=%s articles=%d skipped=%d",
            source.name,
            len(articles),
            len(entries) - len(articles),
        )

        return articles

    def _normalize_entry(
        self,
        entry: dict,
        source: Source,
    ) -> Article | None:
        """Normalize one entry, skipping it when malformed.

        A single unusable entry should not discard an otherwise
        healthy feed, so normalization failures are logged and
        dropped rather than raised. Feeds also publish entries
        that normalize cleanly but fail Article validation, such
        as a relative link, so those are skipped too.
        """
        try:
            return self._normalizer.normalize(entry, source)
        except (RSSNormalizationError, ValidationError):
            logger.warning(
                "Skipping malformed RSS entry: source=%s",
                source.name,
                exc_info=True,
            )

            return None
