"""Tests for the JSON-backed seen store."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.models import Article
from backend.storage.seen_store import JSONSeenStore


def create_article(article_id: str) -> Article:
    """Create a test article."""
    return Article(
        id=article_id,
        title=f"Article {article_id}",
        source="Test Source",
        source_url="https://example.com",
        url=f"https://example.com/{article_id}",
        published_at="2026-01-01T00:00:00Z",
        fetched_at="2026-01-01T01:00:00Z",
        content_hash=f"hash-{article_id}",
    )


def test_filter_new_returns_everything_when_empty(
    tmp_path: Path,
) -> None:
    store = JSONSeenStore(path=tmp_path / "seen.json")

    items = [create_article("1"), create_article("2")]

    assert store.filter_new(items) == items


def test_marked_items_are_filtered_out(
    tmp_path: Path,
) -> None:
    store = JSONSeenStore(path=tmp_path / "seen.json")

    first = create_article("1")
    second = create_article("2")

    store.mark_seen([first])

    assert store.filter_new([first, second]) == [second]


def test_seen_items_survive_a_new_run(
    tmp_path: Path,
) -> None:
    path = tmp_path / "seen.json"

    article = create_article("1")

    JSONSeenStore(path=path).mark_seen([article])

    assert JSONSeenStore(path=path).filter_new(
        [article],
    ) == []


def test_mark_seen_creates_missing_directories(
    tmp_path: Path,
) -> None:
    path = tmp_path / "nested" / "dir" / "seen.json"

    JSONSeenStore(path=path).mark_seen(
        [create_article("1")],
    )

    assert path.exists()


def test_mark_seen_keeps_the_original_timestamp(
    tmp_path: Path,
) -> None:
    path = tmp_path / "seen.json"

    store = JSONSeenStore(path=path)

    article = create_article("1")

    first_time = datetime(2026, 1, 1, tzinfo=UTC)
    later = datetime(2026, 1, 5, tzinfo=UTC)

    store.mark_seen([article], now=first_time)
    store.mark_seen([article], now=later)

    records = json.loads(path.read_text(encoding="utf-8"))

    assert len(records) == 1
    assert records[0]["first_seen"].startswith("2026-01-01")


def test_old_records_are_pruned(tmp_path: Path) -> None:
    path = tmp_path / "seen.json"

    store = JSONSeenStore(path=path, prune_after_days=30)

    old_time = datetime(2026, 1, 1, tzinfo=UTC)

    store.mark_seen([create_article("old")], now=old_time)

    store.mark_seen(
        [create_article("new")],
        now=old_time + timedelta(days=31),
    )

    records = json.loads(path.read_text(encoding="utf-8"))

    assert [record["id"] for record in records] == ["new"]


def test_corrupt_store_starts_empty(
    tmp_path: Path,
) -> None:
    path = tmp_path / "seen.json"

    path.write_text("{not json", encoding="utf-8")

    store = JSONSeenStore(path=path)

    items = [create_article("1")]

    assert store.filter_new(items) == items
