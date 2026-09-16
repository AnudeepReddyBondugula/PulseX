from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.collectors.arxiv.collector import (
    ARXIV_API_URL,
    ArxivCollectionError,
    ArxivCollector,
)
from backend.config.arxiv import ArxivQueryConfig


def create_config() -> ArxivQueryConfig:
    return ArxivQueryConfig(
        query="cat:cs.AI",
        max_results=20,
    )
    
    
def test_collect_returns_raw_response() -> None:
    response = MagicMock()
    response.content = b"<feed></feed>"
    response.text = "<feed></feed>"

    mock_client = MagicMock()
    mock_client.get.return_value = response
    
    # If it is used as a context manager (with statement)
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = response

    with patch(
        "backend.collectors.arxiv.collector.httpx.Client",
        return_value=mock_client,
    ):
        collector = ArxivCollector()

        result = collector.collect(create_config())

    assert result == [
        {
            "raw_xml": "<feed></feed>",
        }
    ]
    
def test_collect_sends_configured_parameters() -> None:
    response = MagicMock()
    response.content = b"<feed></feed>"
    response.text = "<feed></feed>"

    mock_client = MagicMock()
    mock_client.get.return_value = response
    
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = response

    with patch(
        "backend.collectors.arxiv.collector.httpx.Client",
        return_value=mock_client,
    ):
        collector = ArxivCollector()

        collector.collect(create_config())

    mock_client.get.assert_called_once_with(
        ARXIV_API_URL,
        params={
            "search_query": "cat:cs.AI",
            "start": 0,
            "max_results": 20,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
    )
    
    
def test_http_failure_becomes_collection_error() -> None:
    request = httpx.Request(
        "GET",
        ARXIV_API_URL,
    )

    response = httpx.Response(
        503,
        request=request,
    )

    mock_client = MagicMock()
    mock_client.get.side_effect = (
        httpx.HTTPStatusError(
            "Service unavailable",
            request=request,
            response=response,
        )
    )
    
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = response

    with patch(
        "backend.collectors.arxiv.collector.httpx.Client",
        return_value=mock_client,
    ):
        collector = ArxivCollector()

        with pytest.raises(
            ArxivCollectionError,
        ):
            collector.collect(create_config())
            
            
def test_connection_failure_becomes_collection_error() -> None:
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError(
        "Connection failed",
    )
    
    mock_client.__enter__.return_value = mock_client

    with patch(
        "backend.collectors.arxiv.collector.httpx.Client",
        return_value=mock_client,
    ):
        collector = ArxivCollector()

        with pytest.raises(
            ArxivCollectionError,
        ):
            collector.collect(create_config())