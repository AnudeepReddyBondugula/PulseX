from datetime import UTC, datetime

from backend.config.arxiv import (
    ARXIV_CATEGORIES,
    ARXIV_QUERIES,
    TOPIC_ARXIV_CATEGORIES,
    ArxivQueryConfig,
    ArxivSortBy,
    ArxivSortOrder,
    build_category_query,
)
from backend.models.topic import Topic


def test_arxiv_queries_are_configured() -> None:
    assert ARXIV_QUERIES
    assert all(
        isinstance(query, ArxivQueryConfig)
        for query in ARXIV_QUERIES
    )


def test_arxiv_queries_are_immutable() -> None:
    assert isinstance(ARXIV_QUERIES, tuple)


def test_default_query_configuration() -> None:
    config = ArxivQueryConfig(
        query="cat:cs.AI",
    )

    assert config.max_results == 20
    assert config.sort_by == ArxivSortBy.SUBMITTED
    assert config.sort_order == ArxivSortOrder.DESCENDING


def test_query_configuration_is_immutable() -> None:
    config = ArxivQueryConfig(
        query="cat:cs.AI",
    )

    assert config.model_config["frozen"] is True

def test_build_search_query_without_lookback() -> None:
    config = ArxivQueryConfig(query="cat:cs.AI")

    assert config.build_search_query() == "cat:cs.AI"


def test_build_search_query_adds_date_window() -> None:
    config = ArxivQueryConfig(
        query="cat:cs.AI OR cat:cs.LG",
        lookback_hours=24,
    )

    now = datetime(2026, 9, 16, 0, 0, tzinfo=UTC)

    assert config.build_search_query(now) == (
        "(cat:cs.AI OR cat:cs.LG) AND "
        "submittedDate:[202609150000 TO 202609160000]"
    )


def test_categories_cover_every_topic() -> None:
    assert set(TOPIC_ARXIV_CATEGORIES) == set(Topic)


def test_category_query_covers_all_categories() -> None:
    query = build_category_query()

    for category in ARXIV_CATEGORIES:
        assert f"cat:{category}" in query


def test_default_queries_use_a_daily_window() -> None:
    for query in ARXIV_QUERIES:
        assert query.lookback_hours == 24
