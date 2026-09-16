"""RSS entry normalization."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from backend.models import Article, Source


class RSSNormalizationError(Exception):
    """Raised when an RSS entry cannot be normalized."""


class RSSNormalizer:
    """Convert raw RSS entries into PulseX Article models."""

    def normalize(
        self,
        entry: dict[str, Any],
        source: Source,
    ) -> Article:
        """Convert a raw RSS entry into an Article."""
        title = self._get_required_string(entry, "title")
        url = self._get_required_string(entry, "link")

        description = self._get_optional_string(
            entry,
            "summary",
        )

        content = self._extract_content(entry)

        published_at = self._extract_published_at(entry)

        fetched_at = datetime.now(UTC)

        content_hash = self._create_content_hash(
            title=title,
            url=url,
            content=content,
        )

        article_id = self._create_article_id(url)

        return Article(
            id=article_id,
            title=title,
            source=source.name,
            source_url=source.feed_url,
            url=url,
            author=self._get_optional_string(entry, "author"),
            published_at=published_at,
            fetched_at=fetched_at,
            description=description,
            content=content,
            topics=[],
            importance_score=0.0,
            summary=None,
            why_it_matters=None,
            content_hash=content_hash,
        )

    @staticmethod
    def _get_required_string(
        entry: dict[str, Any],
        field: str,
    ) -> str:
        value = entry.get(field)

        if not isinstance(value, str) or not value.strip():
            raise RSSNormalizationError(
                f"Missing required RSS field: {field}"
            )

        return value.strip()

    @staticmethod
    def _get_optional_string(
        entry: dict[str, Any],
        field: str,
    ) -> str | None:
        value = entry.get(field)

        if not isinstance(value, str) or not value.strip():
            return None

        return value.strip()

    @staticmethod
    def _extract_content(
        entry: dict[str, Any],
    ) -> str | None:
        content = entry.get("content")

        if isinstance(content, list) and content:
            first_content = content[0]

            if isinstance(first_content, dict):
                value = first_content.get("value")

                if isinstance(value, str) and value.strip():
                    return value.strip()

        return RSSNormalizer._get_optional_string(
            entry,
            "summary",
        )

    @staticmethod
    def _extract_published_at(
        entry: dict[str, Any],
    ) -> datetime:
        published_parsed = entry.get("published_parsed")

        if published_parsed is not None:
            return datetime(
                published_parsed.tm_year,
                published_parsed.tm_mon,
                published_parsed.tm_mday,
                published_parsed.tm_hour,
                published_parsed.tm_min,
                published_parsed.tm_sec,
                tzinfo=UTC,
            )

        updated_parsed = entry.get("updated_parsed")

        if updated_parsed is not None:
            return datetime(
                updated_parsed.tm_year,
                updated_parsed.tm_mon,
                updated_parsed.tm_mday,
                updated_parsed.tm_hour,
                updated_parsed.tm_min,
                updated_parsed.tm_sec,
                tzinfo=UTC,
            )

        raise RSSNormalizationError(
            "RSS entry has no valid publication date"
        )

    @staticmethod
    def _create_article_id(url: str) -> str:
        return sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _create_content_hash(
        *,
        title: str,
        url: str,
        content: str | None,
    ) -> str:
        value = "|".join(
            [
                title,
                url,
                content or "",
            ]
        )

        return sha256(value.encode("utf-8")).hexdigest()