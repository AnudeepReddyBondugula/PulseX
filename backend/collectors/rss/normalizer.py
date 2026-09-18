"""RSS entry normalization."""

import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from backend.models import Article, Source


IMAGE_MEDIA_PREFIX = "image/"

IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
)

# Matches the first src in an <img> tag, for feeds that ship images
# only inside the HTML body.
INLINE_IMAGE_PATTERN = re.compile(
    r"""<img[^>]+src=["\']([^"\']+)["\']""",
    re.IGNORECASE,
)


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
            image_url=self._extract_image_url(entry),
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

    @classmethod
    def _extract_image_url(
        cls,
        entry: dict[str, Any],
    ) -> str | None:
        """Find a hero image for the entry, if it has one.

        Feeds advertise images in several places and agree on
        none of them, so each known location is tried in turn,
        most explicit first. Returning None is normal: plenty of
        feeds carry no image at all.
        """
        for extract in (
            cls._image_from_media_thumbnail,
            cls._image_from_media_content,
            cls._image_from_enclosures,
            cls._image_from_links,
            cls._image_from_html,
        ):
            url = extract(entry)

            if url is not None:
                return url

        return None

    @staticmethod
    def _image_from_media_thumbnail(
        entry: dict[str, Any],
    ) -> str | None:
        """Read a media:thumbnail element."""
        thumbnails = entry.get("media_thumbnail")

        if not isinstance(thumbnails, list):
            return None

        for thumbnail in thumbnails:
            if isinstance(thumbnail, dict):
                url = thumbnail.get("url")

                if _is_http_url(url):
                    return url

        return None

    @staticmethod
    def _image_from_media_content(
        entry: dict[str, Any],
    ) -> str | None:
        """Read a media:content element declaring an image."""
        contents = entry.get("media_content")

        if not isinstance(contents, list):
            return None

        for content in contents:
            if not isinstance(content, dict):
                continue

            url = content.get("url")

            if not _is_http_url(url):
                continue

            medium = content.get("medium")
            content_type = content.get("type", "")

            if (
                medium == "image"
                or str(content_type).startswith(
                    IMAGE_MEDIA_PREFIX,
                )
                or _looks_like_image(url)
            ):
                return url

        return None

    @staticmethod
    def _image_from_enclosures(
        entry: dict[str, Any],
    ) -> str | None:
        """Read an enclosure whose type is an image."""
        enclosures = entry.get("enclosures")

        if not isinstance(enclosures, list):
            return None

        for enclosure in enclosures:
            if not isinstance(enclosure, dict):
                continue

            url = enclosure.get("href") or enclosure.get("url")

            if not _is_http_url(url):
                continue

            content_type = str(enclosure.get("type", ""))

            if content_type.startswith(
                IMAGE_MEDIA_PREFIX
            ) or _looks_like_image(url):
                return url

        return None

    @staticmethod
    def _image_from_links(
        entry: dict[str, Any],
    ) -> str | None:
        """Read a link element pointing at an image."""
        links = entry.get("links")

        if not isinstance(links, list):
            return None

        for link in links:
            if not isinstance(link, dict):
                continue

            url = link.get("href")

            if not _is_http_url(url):
                continue

            content_type = str(link.get("type", ""))

            if content_type.startswith(IMAGE_MEDIA_PREFIX):
                return url

        return None

    @classmethod
    def _image_from_html(
        cls,
        entry: dict[str, Any],
    ) -> str | None:
        """Fall back to the first image in the entry body."""
        for field in ("content", "summary"):
            value = entry.get(field)

            if isinstance(value, list) and value:
                first = value[0]

                value = (
                    first.get("value")
                    if isinstance(first, dict)
                    else None
                )

            if not isinstance(value, str):
                continue

            match = INLINE_IMAGE_PATTERN.search(value)

            if match and _is_http_url(match.group(1)):
                return match.group(1)

        return None

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


def _is_http_url(value: Any) -> bool:
    """Whether a value is a usable absolute HTTP(S) URL."""
    return isinstance(value, str) and value.startswith(
        ("http://", "https://"),
    )


def _looks_like_image(url: str) -> bool:
    """Whether a URL's path ends in a known image extension."""
    path = url.split("?")[0].split("#")[0].lower()

    return path.endswith(IMAGE_EXTENSIONS)
