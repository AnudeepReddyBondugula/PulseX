"""
test_fetch_papers.py — Unit tests for fetch_papers.py

Run with: pytest tests/test_fetch_papers.py
No real network calls are made — feedparser.parse is mocked throughout.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from pipeline import fetch_papers


def _time_tuple(dt: datetime):
    return dt.timetuple()[:9]


def _fake_entry(link="https://arxiv.org/abs/1234.5678", title="Paper A",
                 summary="Abstract A", published_dt=None):
    published_dt = published_dt or datetime.now(timezone.utc)
    return {
        "link": link,
        "title": title,
        "summary": summary,
        "published_parsed": _time_tuple(published_dt),
    }


def _fake_parsed(entries, bozo=False, bozo_exception=None):
    return SimpleNamespace(bozo=bozo, bozo_exception=bozo_exception, entries=entries)


def test_make_id_is_deterministic():
    assert fetch_papers._make_id("https://arxiv.org/abs/1") == fetch_papers._make_id(
        "https://arxiv.org/abs/1"
    )


def test_is_within_lookback_true_for_recent():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=2)).isoformat()
    assert fetch_papers._is_within_lookback(recent, now) is True


def test_is_within_lookback_false_for_old():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=48)).isoformat()
    assert fetch_papers._is_within_lookback(old, now) is False


def test_is_within_lookback_false_for_missing():
    now = datetime.now(timezone.utc)
    assert fetch_papers._is_within_lookback(None, now) is False


def test_build_query_url_includes_category():
    url = fetch_papers._build_query_url("cs.AI")
    assert "cat%3Acs.AI" in url or "cat:cs.AI" in url
    assert "sortBy=submittedDate" in url


@patch("pipeline.fetch_papers.feedparser.parse")
def test_fetch_category_includes_recent_paper(mock_parse):
    now = datetime.now(timezone.utc)
    mock_parse.return_value = _fake_parsed([_fake_entry(published_dt=now - timedelta(hours=1))])
    items = fetch_papers.fetch_category("cs.AI", now=now)
    assert len(items) == 1
    assert items[0].source == "cs.AI"


@patch("pipeline.fetch_papers.feedparser.parse")
def test_fetch_category_excludes_old_paper(mock_parse):
    now = datetime.now(timezone.utc)
    mock_parse.return_value = _fake_parsed(
        [_fake_entry(published_dt=now - timedelta(hours=72))]
    )
    items = fetch_papers.fetch_category("cs.AI", now=now)
    assert len(items) == 0


@patch("pipeline.fetch_papers.feedparser.parse")
def test_fetch_category_skips_entries_missing_link_or_title(mock_parse):
    now = datetime.now(timezone.utc)
    mock_parse.return_value = _fake_parsed(
        [
            {"link": "", "title": "No link", "summary": "", "published_parsed": _time_tuple(now)},
            _fake_entry(link="https://arxiv.org/abs/2", title="Valid", published_dt=now),
        ]
    )
    items = fetch_papers.fetch_category("cs.AI", now=now)
    assert len(items) == 1
    assert items[0].title == "Valid"


@patch("pipeline.fetch_papers.feedparser.parse")
def test_fetch_category_returns_empty_list_on_exception(mock_parse):
    mock_parse.side_effect = Exception("network error")
    assert fetch_papers.fetch_category("cs.AI") == []


@patch("pipeline.fetch_papers.fetch_category")
def test_fetch_all_papers_aggregates_across_categories(mock_fetch_category):
    mock_fetch_category.side_effect = lambda cat, now=None: [_dummy_item(cat)]
    items = fetch_papers.fetch_all_papers()
    assert len(items) == len(fetch_papers.ARXIV_CATEGORIES)


def _dummy_item(category):
    return fetch_papers.PaperItem(
        id="abc123", title="Dummy", link="https://arxiv.org/abs/x",
        source=category, published_at=None, raw_summary=""
    )