"""Persistence for content PulseX has already delivered."""

import json
import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from backend.models import Article, ResearchPaper


logger = logging.getLogger(__name__)


ContentItem = Article | ResearchPaper

DEFAULT_STORE_PATH = Path("data/seen_items.json")

DEFAULT_PRUNE_AFTER_DAYS = 60


class SeenRecord(BaseModel):
    """One item PulseX has already sent."""

    id: str
    first_seen: datetime


class SeenStore(Protocol):
    """Tracks which items have already been delivered.

    Deliberately narrow so the JSON implementation can be
    swapped for Firestore without touching callers.
    """

    def filter_new(
        self,
        items: Sequence[ContentItem],
    ) -> list[ContentItem]:
        """Return only the items not yet delivered."""
        ...

    def mark_seen(
        self,
        items: Iterable[ContentItem],
    ) -> None:
        """Record items as delivered."""
        ...


class JSONSeenStore:
    """A seen store backed by a local JSON file."""

    def __init__(
        self,
        path: Path = DEFAULT_STORE_PATH,
        prune_after_days: int = DEFAULT_PRUNE_AFTER_DAYS,
    ) -> None:
        self._path = path
        self._prune_after_days = prune_after_days
        self._records: dict[str, SeenRecord] = {}
        self._load()

    def filter_new(
        self,
        items: Sequence[ContentItem],
    ) -> list[ContentItem]:
        """Return only the items not yet delivered."""
        new_items = [
            item
            for item in items
            if item.id not in self._records
        ]

        logger.info(
            "Filtered seen content: total=%d new=%d",
            len(items),
            len(new_items),
        )

        return new_items

    def mark_seen(
        self,
        items: Iterable[ContentItem],
        *,
        now: datetime | None = None,
    ) -> None:
        """Record items as delivered and persist the store.

        Call this only once delivery has succeeded: an item
        marked seen is never offered again, so marking before
        a failed send would drop it permanently.
        """
        current_time = now or datetime.now(UTC)

        for item in items:
            self._records.setdefault(
                item.id,
                SeenRecord(
                    id=item.id,
                    first_seen=current_time,
                ),
            )

        self._prune(current_time)
        self._save()

    def _prune(self, now: datetime) -> None:
        """Drop records old enough that they cannot recur."""
        cutoff = now - timedelta(
            days=self._prune_after_days,
        )

        self._records = {
            record_id: record
            for record_id, record in self._records.items()
            if record.first_seen >= cutoff
        }

    def _load(self) -> None:
        """Read the store, tolerating a missing file."""
        if not self._path.exists():
            logger.info(
                "No seen store at %s, starting empty",
                self._path,
            )

            return

        try:
            raw = json.loads(
                self._path.read_text(encoding="utf-8"),
            )

            self._records = {
                record["id"]: SeenRecord(**record)
                for record in raw
            }
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
        ):
            # A corrupt store should cost us one day of repeats,
            # not the whole run.
            logger.exception(
                "Could not read seen store at %s, starting empty",
                self._path,
            )

            self._records = {}

            return

        logger.info(
            "Loaded seen store: path=%s records=%d",
            self._path,
            len(self._records),
        )

    def _save(self) -> None:
        """Write the store, creating the directory if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        payload = [
            json.loads(record.model_dump_json())
            for record in self._records.values()
        ]

        self._path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "Saved seen store: path=%s records=%d",
            self._path,
            len(self._records),
        )
