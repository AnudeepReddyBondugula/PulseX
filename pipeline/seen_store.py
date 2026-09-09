"""
seen_store.py — Tracks which news/paper items have already been processed,
so the daily run only summarizes genuinely new content.

Backed by a local JSON file for now; the interface (is_seen / filter_new /
mark_seen) is deliberately storage-agnostic so it can be pointed at
Firestore later without changing any calling code.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Protocol

from pydantic import BaseModel

from pipeline.config import get_logger

logger = get_logger(__name__)

DEFAULT_STORE_PATH = Path("data/seen_items.json")
DEFAULT_PRUNE_AFTER_DAYS = 60  # keep the file from growing forever


class _HasId(Protocol):
    id: str


class SeenRecord(BaseModel):
    id: str
    first_seen: str  # ISO 8601


class SeenStore:
    def __init__(self, path: Path = DEFAULT_STORE_PATH):
        self.path = path
        self._records: dict[str, SeenRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            logger.info("No existing seen-store file at %s — starting fresh", self.path)
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._records = {
                item_id: SeenRecord.model_validate(record) for item_id, record in raw.items()
            }
            logger.info("Loaded %d seen records from %s", len(self._records), self.path)
        except (json.JSONDecodeError, ValueError) as exc:
            # Corrupt file shouldn't crash the pipeline — treat as empty and
            # let it rebuild; the worst case is a few duplicate summaries.
            logger.warning(
                "Seen-store file at %s was unreadable (%s) — starting fresh", self.path, exc
            )
            self._records = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {item_id: record.model_dump() for item_id, record in self._records.items()}
        # Write to a temp file then replace, so a crash mid-write can't corrupt
        # the existing store.
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)
        logger.info("Saved %d seen records to %s", len(self._records), self.path)

    def is_seen(self, item_id: str) -> bool:
        return item_id in self._records

    def mark_seen(self, item_ids: Iterable[str], now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        for item_id in item_ids:
            if item_id not in self._records:
                self._records[item_id] = SeenRecord(id=item_id, first_seen=now.isoformat())

    def filter_new(self, items: List[_HasId]) -> List[_HasId]:
        """Return only the items whose .id hasn't been seen before."""
        new_items = [item for item in items if not self.is_seen(item.id)]
        logger.info(
            "filter_new: %d new out of %d total items", len(new_items), len(items)
        )
        return new_items

    def prune(self, older_than_days: int = DEFAULT_PRUNE_AFTER_DAYS, now: datetime | None = None) -> int:
        """
        Remove records older than `older_than_days`. Safe to run periodically —
        an item won't reappear as "new" just because its record aged out,
        since sources don't re-publish old items under the same link.
        Returns the number of records removed.
        """
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=older_than_days)
        before_count = len(self._records)
        self._records = {
            item_id: record
            for item_id, record in self._records.items()
            if datetime.fromisoformat(record.first_seen) > cutoff
        }
        removed = before_count - len(self._records)
        if removed:
            logger.info("Pruned %d records older than %d days", removed, older_than_days)
        return removed