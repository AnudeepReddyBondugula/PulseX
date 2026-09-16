"""Content collection orchestration."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from backend.collectors.arxiv.service import (
    ArxivIngestionError,
    ArxivIngestionService,
)
from backend.collectors.rss.service import (
    RSSIngestionError,
    RSSIngestionService,
)
from backend.config.arxiv import ARXIV_QUERIES, ArxivQueryConfig
from backend.config.sources import RSS_SOURCES
from backend.models import Article, ResearchPaper, Source


logger = logging.getLogger(__name__)


ContentItem = Article | ResearchPaper


@dataclass(frozen=True)
class CollectionFailure:
    """A source that could not be collected."""

    source: str
    error: str


@dataclass(frozen=True)
class CollectionResult:
    """Everything gathered during one collection run."""

    articles: list[Article] = field(default_factory=list)
    papers: list[ResearchPaper] = field(default_factory=list)
    failures: list[CollectionFailure] = field(
        default_factory=list,
    )

    @property
    def items(self) -> list[ContentItem]:
        """All collected items, ready for processing."""
        return [*self.articles, *self.papers]


class CollectionService:
    """Collect content from every configured source.

    One unreachable feed should not cost us the whole daily
    run, so failures are recorded per source and the
    remaining sources are still collected.
    """

    def __init__(
        self,
        rss_service: RSSIngestionService,
        arxiv_service: ArxivIngestionService,
    ) -> None:
        self._rss_service = rss_service
        self._arxiv_service = arxiv_service

    def collect(
        self,
        *,
        sources: Sequence[Source] = RSS_SOURCES,
        queries: Sequence[ArxivQueryConfig] = ARXIV_QUERIES,
    ) -> CollectionResult:
        """Collect articles and papers from all sources."""
        logger.info(
            "Starting collection: sources=%d queries=%d",
            len(sources),
            len(queries),
        )

        articles: list[Article] = []
        papers: list[ResearchPaper] = []
        failures: list[CollectionFailure] = []

        for source in sources:
            try:
                articles.extend(
                    self._rss_service.ingest(source),
                )
            except RSSIngestionError as exc:
                failures.append(
                    CollectionFailure(
                        source=source.name,
                        error=str(exc),
                    )
                )

        for query in queries:
            try:
                papers.extend(
                    self._arxiv_service.ingest(query),
                )
            except ArxivIngestionError as exc:
                failures.append(
                    CollectionFailure(
                        source=f"arxiv:{query.query}",
                        error=str(exc),
                    )
                )

        logger.info(
            "Completed collection: articles=%d papers=%d failures=%d",
            len(articles),
            len(papers),
            len(failures),
        )

        return CollectionResult(
            articles=articles,
            papers=papers,
            failures=failures,
        )
