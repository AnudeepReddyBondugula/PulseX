"""arXiv API collection."""

import logging
from typing import Any

import httpx

from backend.config.arxiv import ArxivQueryConfig


logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"


class ArxivCollectionError(Exception):
    """Raised when arXiv data cannot be collected."""


class ArxivCollector:
    """Collect raw entries from the arXiv API."""

    def collect(
        self,
        config: ArxivQueryConfig,
    ) -> list[dict[str, Any]]:
        """Collect raw arXiv entries for a configured query."""
        search_query = config.build_search_query()

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": config.max_results,
            "sortBy": config.sort_by.value,
            "sortOrder": config.sort_order.value,
        }

        logger.info(
            "Collecting arXiv papers: query=%s max_results=%d",
            search_query,
            config.max_results,
        )

        timeout = httpx.Timeout(
            connect=10.0,
            read=30.0,
            write=10.0,
            pool=10.0,
        )

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(
                    ARXIV_API_URL,
                    params=params,
                )

                response.raise_for_status()

        except httpx.HTTPError as exc:
            logger.exception(
                "Failed to collect arXiv papers: query=%s",
                config.query,
            )

            raise ArxivCollectionError(
                f"Failed to collect arXiv papers: {config.query}"
            ) from exc

        logger.info(
            "arXiv response received: query=%s bytes=%d",
            config.query,
            len(response.content),
        )

        return [
            {
                "raw_xml": response.text,
            },
        ]