from backend.config.arxiv import (
    ARXIV_QUERIES,
    ArxivQueryConfig,
    ArxivSortBy,
    ArxivSortOrder,
)


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