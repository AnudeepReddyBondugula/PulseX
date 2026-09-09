"""
fetch_papers.py — Fetches newly published papers from arXiv.

FR-2: Fetch newly published papers daily from 4+ arXiv categories.
FR-6: Every summary includes a traceable source/reference link.

arXiv's public API returns an Atom feed (no API key required) — reused via
feedparser, same library as fetch_news.py, for consistency (Section 9:
"Free, official, no key required").

Deduplication happens separately (seen_store.py, Module A2.4) — this module
only fetches, normalizes, and time-filters raw items.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlencode

import feedparser
from pydantic import BaseModel, Field

from pipeline.config import ARXIV_CATEGORIES, get_logger

import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

logger = get_logger(__name__)

ARXIV_API_BASE = "http://export.arxiv.org/api/query"
MAX_RESULTS_PER_CATEGORY = 50  # per Assumption in Section 4.3: fetched, then time-filtered
LOOKBACK_HOURS = 24            # "latest" = published in roughly the last 24 hours


class PaperItem(BaseModel):
    id: str                         # stable hash of the arXiv link, used for dedupe (A2.4)
    title: str = Field(min_length=1)
    link: str = Field(min_length=1)
    source: str                     # arXiv category, for traceability (FR-6)
    published_at: Optional[str] = None  # ISO 8601 string, or None if unavailable
    raw_summary: str = ""           # abstract, NOT the LLM summary (A2.5)


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


def _is_within_lookback(published_at: Optional[str], now: datetime) -> bool:
    """
    True if published_at is within LOOKBACK_HOURS of `now`.
    If published_at is missing, the item is excluded (fails safe, per FR-6 —
    we can't claim it's "latest" if we can't verify when it was published).
    """
    if published_at is None:
        return False
    published_dt = datetime.fromisoformat(published_at)
    return (now - published_dt) <= timedelta(hours=LOOKBACK_HOURS)


def _build_query_url(category: str) -> str:
    params = {
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": MAX_RESULTS_PER_CATEGORY,
    }
    return f"{ARXIV_API_BASE}?{urlencode(params)}"


def fetch_category(category: str, now: Optional[datetime] = None) -> List[PaperItem]:
    """
    Fetch and time-filter papers for a single arXiv category.
    Never raises on a bad/unreachable response — logs a warning and returns
    [] so one broken category doesn't take down the whole daily pipeline run.
    """
    now = now or datetime.now(timezone.utc)
    items: List[PaperItem] = []
    url = _build_query_url(category)

    try:
        parsed = feedparser.parse(url, )  # arXiv's SSL cert is valid, but some environments may not have up-to-date CA bundle
    except Exception as exc:
        logger.warning("Failed to fetch arXiv category %s: %s", category, exc)
        return items

    if parsed.bozo:
        logger.warning(
            "arXiv category %s returned malformed feed (bozo): %s",
            category,
            getattr(parsed, "bozo_exception", None),
        )

    for entry in parsed.entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            logger.warning("Skipping arXiv entry with missing link/title in %s", category)
            continue

        published_at = _parse_published(entry)
        if not _is_within_lookback(published_at, now):
            continue

        items.append(
            PaperItem(
                id=_make_id(link),
                title=" ".join(title.split()),  # arXiv titles often have stray newlines
                link=link,
                source=category,
                published_at=published_at,
                raw_summary=entry.get("summary", ""),
            )
        )

    logger.info(
        "Fetched %d papers within %dh window from %s", len(items), LOOKBACK_HOURS, category
    )
    return items


def fetch_all_papers() -> List[PaperItem]:
    """
    Fetch every configured arXiv category (FR-2).
    Returns a flat list of PaperItem across all categories — un-deduped.
    """
    all_items: List[PaperItem] = []
    for category in ARXIV_CATEGORIES:
        all_items.extend(fetch_category(category))

    logger.info(
        "fetch_all_papers: %d total papers across %d categories",
        len(all_items),
        len(ARXIV_CATEGORIES),
    )
    return all_items