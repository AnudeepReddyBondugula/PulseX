"""
test_seen_store.py — Unit tests for seen_store.py

Run with: pytest tests/test_seen_store.py
Uses pytest's tmp_path fixture — no real files touched outside the test run.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pipeline.seen_store import SeenStore


@dataclass
class _FakeItem:
    id: str


def test_new_store_has_no_seen_items(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    assert store.is_seen("abc") is False


def test_mark_seen_then_is_seen_true(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    store.mark_seen(["abc"])
    assert store.is_seen("abc") is True


def test_filter_new_excludes_already_seen(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    store.mark_seen(["abc"])
    items = [_FakeItem(id="abc"), _FakeItem(id="def")]
    result = store.filter_new(items)
    assert [item.id for item in result] == ["def"]


def test_save_and_reload_persists_records(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path=path)
    store.mark_seen(["abc", "def"])
    store.save()

    reloaded = SeenStore(path=path)
    assert reloaded.is_seen("abc") is True
    assert reloaded.is_seen("def") is True


def test_corrupt_file_starts_fresh_instead_of_crashing(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = SeenStore(path=path)  # should not raise
    assert store.is_seen("anything") is False


def test_prune_removes_old_records(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=90)
    store.mark_seen(["old_item"], now=old_time)
    store.mark_seen(["recent_item"], now=now)

    removed = store.prune(older_than_days=60, now=now)

    assert removed == 1
    assert store.is_seen("old_item") is False
    assert store.is_seen("recent_item") is True


def test_mark_seen_does_not_overwrite_existing_first_seen(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    early = datetime.now(timezone.utc) - timedelta(days=10)
    later = datetime.now(timezone.utc)

    store.mark_seen(["abc"], now=early)
    store.mark_seen(["abc"], now=later)  # should be a no-op for existing id

    record = store._records["abc"]
    assert record.first_seen == early.isoformat()