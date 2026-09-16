"""Deterministic content deduplication."""

from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit
import re

from backend.models.article import Article
from backend.models.research_paper import ResearchPaper


ContentItem = Article | ResearchPaper


@dataclass(frozen=True)
class DeduplicationResult:
    """Result of deterministic deduplication."""

    unique: list[ContentItem]
    duplicates: list[ContentItem]


class Deduplicator:
    """Remove duplicate content using deterministic identity signals."""

    def deduplicate(
        self,
        items: list[ContentItem],
    ) -> DeduplicationResult:
        """Split content into unique items and duplicates."""
        unique: list[ContentItem] = []
        duplicates: list[ContentItem] = []

        seen_content_hashes: set[str] = set()
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()

        for item in items:
            content_hash = self._content_hash(item)
            canonical_url = self._canonical_url(str(item.url))
            normalized_title = self._normalize_title(item.title)

            is_duplicate = (
                content_hash in seen_content_hashes
                or canonical_url in seen_urls
                or normalized_title in seen_titles
            )

            if is_duplicate:
                duplicates.append(item)
                continue

            unique.append(item)

            seen_content_hashes.add(content_hash)
            seen_urls.add(canonical_url)
            seen_titles.add(normalized_title)

        return DeduplicationResult(
            unique=unique,
            duplicates=duplicates,
        )

    @staticmethod
    def _content_hash(item: ContentItem) -> str:
        """Return a deterministic content identity hash.

        Only articles carry a precomputed hash from their
        collector; papers are hashed from their fields here.
        """
        content_hash = getattr(item, "content_hash", None)

        if content_hash:
            return content_hash

        content = "|".join(
            (
                item.title,
                str(item.url),
                item.summary or "",
            )
        )

        return sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_url(url: str) -> str:
        """Normalize a URL for deterministic comparison."""
        parsed = urlsplit(url)

        scheme = parsed.scheme.lower()
        hostname = (parsed.hostname or "").lower()

        port = parsed.port

        if port is not None:
            if not (
                (scheme == "http" and port == 80)
                or (scheme == "https" and port == 443)
            ):
                hostname = f"{hostname}:{port}"

        path = parsed.path.rstrip("/") or "/"

        return urlunsplit(
            (
                scheme,
                hostname,
                path,
                parsed.query,
                "",
            )
        )

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize a title for exact comparison."""
        normalized = title.strip().lower()
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized