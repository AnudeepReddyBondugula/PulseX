"""arXiv entry normalization."""

import logging
from datetime import datetime
from urllib.parse import urlparse

from pydantic import ValidationError

from backend.collectors.arxiv.parser import RawArxivEntry
from backend.models.research_paper import ResearchPaper


logger = logging.getLogger(__name__)


class ArxivNormalizationError(Exception):
    """Raised when an arXiv entry cannot be normalized."""


class ArxivNormalizer:
    """Convert raw arXiv entries into ResearchPaper models."""

    def normalize(
        self,
        entry: RawArxivEntry,
    ) -> ResearchPaper:
        """Normalize one raw arXiv entry."""
        try:
            arxiv_id = self._extract_arxiv_id(entry.id_url)

            published_at = self._parse_datetime(
                entry.published,
                field_name="published",
            )

            updated_at = self._parse_datetime(
                entry.updated,
                field_name="updated",
            )

            url = entry.abstract_url or entry.id_url

            return ResearchPaper(
                id=arxiv_id,
                arxiv_id=arxiv_id,
                title=entry.title,
                authors=entry.authors,
                abstract=entry.summary,
                url=url,
                published_at=published_at,
                updated_at=updated_at,
                categories=entry.categories,
                topics=[],
                importance_score=0.0,
                summary=None,
                why_it_matters=None,
            )

        except ValidationError as exc:
            logger.exception(
                "Failed to validate arXiv paper: id_url=%s",
                entry.id_url,
            )
            raise ArxivNormalizationError(
                f"Invalid arXiv paper: {entry.id_url}"
            ) from exc

        except (ValueError, TypeError) as exc:
            logger.exception(
                "Failed to normalize arXiv paper: id_url=%s",
                entry.id_url,
            )
            raise ArxivNormalizationError(
                f"Failed to normalize arXiv paper: {entry.id_url}"
            ) from exc

    @staticmethod
    def _extract_arxiv_id(id_url: str) -> str:
        """Extract the arXiv identifier from an arXiv URL."""
        parsed = urlparse(id_url)

        path = parsed.path.rstrip("/")

        if "/abs/" in path:
            arxiv_id = path.split("/abs/", maxsplit=1)[1]
        else:
            arxiv_id = path.rsplit("/", maxsplit=1)[-1]

        arxiv_id = arxiv_id.strip()

        if not arxiv_id:
            raise ValueError(
                f"Could not extract arXiv ID from: {id_url}"
            )

        return arxiv_id

    @staticmethod
    def _parse_datetime(
        value: str,
        *,
        field_name: str,
    ) -> datetime:
        """Parse an arXiv ISO-8601 timestamp."""
        normalized_value = value.strip()

        if normalized_value.endswith("Z"):
            normalized_value = (
                normalized_value[:-1] + "+00:00"
            )

        try:
            return datetime.fromisoformat(normalized_value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid {field_name} timestamp: {value}"
            ) from exc