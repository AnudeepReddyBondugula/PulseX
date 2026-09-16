"""End-to-end digest pipeline."""

import logging
from dataclasses import dataclass
from datetime import datetime

from backend.collectors.arxiv.collector import ArxivCollector
from backend.collectors.arxiv.normalizer import ArxivNormalizer
from backend.collectors.arxiv.parser import ArxivParser
from backend.collectors.arxiv.service import ArxivIngestionService
from backend.collectors.rss.collector import RSSCollector
from backend.collectors.rss.normalizer import RSSNormalizer
from backend.collectors.rss.service import RSSIngestionService
from backend.processors.deduplication.processor import Deduplicator
from backend.processors.ranking.processor import RankingProcessor
from backend.processors.relevance.processor import RelevanceProcessor
from backend.processors.topics.processor import TopicExtractor
from backend.services.collection import (
    CollectionFailure,
    CollectionService,
)
from backend.services.content_processing import (
    ContentProcessingService,
    ProcessedContent,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestResult:
    """Outcome of one end-to-end digest run."""

    processed: ProcessedContent
    failures: list[CollectionFailure]


class DigestPipeline:
    """Run collection and deterministic processing together."""

    def __init__(
        self,
        collection_service: CollectionService,
        processing_service: ContentProcessingService,
    ) -> None:
        self._collection_service = collection_service
        self._processing_service = processing_service

    def run(
        self,
        *,
        now: datetime | None = None,
    ) -> DigestResult:
        """Collect from every source, then process the results."""
        collection = self._collection_service.collect()

        logger.info(
            "Processing collected content: items=%d",
            len(collection.items),
        )

        processed = self._processing_service.process(
            collection.items,
            now=now,
        )

        logger.info(
            "Digest run complete: ranked=%d duplicates=%d irrelevant=%d",
            len(processed.items),
            len(processed.duplicates),
            len(processed.irrelevant),
        )

        return DigestResult(
            processed=processed,
            failures=collection.failures,
        )


def create_digest_pipeline() -> DigestPipeline:
    """Build a pipeline wired with the default components."""
    collection_service = CollectionService(
        rss_service=RSSIngestionService(
            collector=RSSCollector(),
            normalizer=RSSNormalizer(),
        ),
        arxiv_service=ArxivIngestionService(
            collector=ArxivCollector(),
            parser=ArxivParser(),
            normalizer=ArxivNormalizer(),
        ),
    )

    processing_service = ContentProcessingService(
        deduplicator=Deduplicator(),
        relevance_processor=RelevanceProcessor(),
        topic_extractor=TopicExtractor(),
        ranking_processor=RankingProcessor(),
    )

    return DigestPipeline(
        collection_service=collection_service,
        processing_service=processing_service,
    )
