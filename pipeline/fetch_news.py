"""
fetch_news.py — Fetches new articles from the fixed RSS source list.

FR-1: Fetch new articles daily from 6-10 fixed, trusted RSS sources.
FR-6: Every summary includes a traceable source/reference link.

Deduplication happens separately — this module
only fetches and normalizes raw items.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

import feedparser
from pydantic import BaseModel, Field

from pipeline.config import RSS_SOURCES, get_logger

logger = get_logger(__name__)


class NewsItem(BaseModel):
    id: str                        # stable hash of the link, used for dedupe
    title: str = Field(min_length=1)
    link: str = Field(min_length=1)
    source: str                    # feed/domain name, for traceability
    published_at: Optional[str] = None  # ISO 8601 string, or None if unavailable
    raw_summary: str = ""          # short RSS description, NOT the LLM summary


def _make_id(link: str) -> str:
    """Stable, deterministic ID for dedupe — same link always hashes the same."""
    return hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]


def _parse_published(entry) -> Optional[str]:
    """Best-effort extraction of a published timestamp as ISO 8601."""
    published_parsed = entry.get("published_parsed")
    if published_parsed:
        dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    return None


def fetch_feed(url: str) -> List[NewsItem]:
    """
    Fetch and normalize a single RSS feed.
    Never raises on a bad/unreachable feed — logs a warning and returns []
    so one broken source doesn't take down the whole daily pipeline run.
    """
    items: List[NewsItem] = []
    try:
        parsed = feedparser.parse(url)
    except Exception as exc:
        logger.warning("Failed to fetch feed %s: %s", url, exc)
        return items

    if parsed.bozo:
        logger.warning(
            "Feed %s returned malformed XML (bozo): %s",
            url,
            getattr(parsed, "bozo_exception", None),
        )

    source_name = parsed.feed.get("title", url) if hasattr(parsed, "feed") else url

    for entry in parsed.entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            logger.warning("Skipping entry with missing link/title from %s", url)
            continue

        items.append(
            NewsItem(
                id=_make_id(link),
                title=title,
                link=link,
                source=source_name,
                published_at=_parse_published(entry),
                raw_summary=entry.get("summary", ""),
            )
        )

    logger.info("Fetched %d items from %s", len(items), source_name)
    return items


def fetch_all_news() -> List[NewsItem]:
    """
    Fetch every configured RSS source (FR-1).
    Returns a flat list of NewsItem across all sources — un-deduped.
    """
    all_items: List[NewsItem] = []
    for url in RSS_SOURCES:
        all_items.extend(fetch_feed(url))

    logger.info(
        "fetch_all_news: %d total items across %d sources",
        len(all_items),
        len(RSS_SOURCES),
    )
    return all_items