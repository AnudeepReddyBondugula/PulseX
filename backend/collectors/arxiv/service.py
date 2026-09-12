"""arXiv ingestion orchestration."""

import logging

from backend.collectors.arxiv.collector import (
    ArxivCollector,
    ArxivCollectionError,
)
from backend.collectors.arxiv.normalizer import (
    ArxivNormalizationError,
    ArxivNormalizer,
)
from backend.collectors.arxiv.parser import (
    ArxivParser,
    ArxivParsingError,
)
from backend.config.arxiv import ArxivQueryConfig
from backend.models.research_paper import ResearchPaper


logger = logging.getLogger(__name__)


class ArxivIngestionError(Exception):
    """Raised when arXiv ingestion fails."""


class ArxivIngestionService:
    """Orchestrate arXiv collection, parsing, and normalization."""

    def __init__(
        self,
        collector: ArxivCollector,
        parser: ArxivParser,
        normalizer: ArxivNormalizer,
    ) -> None:
        self._collector = collector
        self._parser = parser
        self._normalizer = normalizer

    def ingest(
        self,
        config: ArxivQueryConfig,
    ) -> list[ResearchPaper]:
        """Collect and normalize papers for one arXiv query."""
        logger.info(
            "Starting arXiv ingestion: query=%s",
            config.query,
        )

        try:
            raw_responses = self._collector.collect(config)

            papers: list[ResearchPaper] = []

            for raw_response in raw_responses:
                raw_xml = raw_response["raw_xml"]

                entries = self._parser.parse(raw_xml)

                for entry in entries:
                    paper = self._normalizer.normalize(entry)
                    papers.append(paper)

        except (
            ArxivCollectionError,
            ArxivParsingError,
            ArxivNormalizationError,
        ) as exc:
            logger.exception(
                "arXiv ingestion failed: query=%s",
                config.query,
            )
            raise ArxivIngestionError(
                f"Failed to ingest arXiv query: {config.query}"
            ) from exc

        logger.info(
            "Completed arXiv ingestion: query=%s papers=%d",
            config.query,
            len(papers),
        )

        return papers