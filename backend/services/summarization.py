"""AI enrichment of processed content."""

import logging
import re

from backend.llm.base import LLMProvider, LLMProviderError
from backend.models import Article, ResearchPaper
from backend.services.content_processing import ProcessedItem


logger = logging.getLogger(__name__)


NEWS_PROMPT = """\
Summarize this AI technology news article for a daily reader digest.

Reply in exactly this format, with no preamble and no markdown:
SUMMARY: <2-3 plain-English sentences on what happened>
WHY IT MATTERS: <1 sentence on why a reader should care>

Title: {title}

Content: {content}
"""

PAPER_PROMPT = """\
Explain this AI research paper to a curious non-specialist. Avoid jargon
wherever a simpler word works, and never assume the reader knows the
field's terminology.

Reply in exactly this format, with no preamble and no markdown:
SUMMARY: <2-3 simple sentences on what the researchers did and found>
WHY IT MATTERS: <1 sentence on why this result is interesting>

Title: {title}

Abstract: {abstract}
"""

SUMMARY_PATTERN = re.compile(
    r"SUMMARY:\s*(.+?)(?=WHY IT MATTERS:|$)",
    re.IGNORECASE | re.DOTALL,
)

WHY_PATTERN = re.compile(
    r"WHY IT MATTERS:\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


class SummarizationService:
    """Fill in AI summaries for processed content."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def summarize(
        self,
        items: list[ProcessedItem],
    ) -> list[ProcessedItem]:
        """Return items enriched with summaries.

        A provider failure on one item leaves that item
        unsummarized rather than losing the whole brief.
        """
        logger.info(
            "Summarizing content: items=%d",
            len(items),
        )

        return [
            self._summarize_item(item) for item in items
        ]

    def _summarize_item(
        self,
        processed: ProcessedItem,
    ) -> ProcessedItem:
        """Summarize one item, keeping it on failure."""
        prompt = self._build_prompt(processed.item)

        try:
            response = self._provider.generate(prompt)
        except LLMProviderError:
            logger.exception(
                "Could not summarize item: id=%s",
                processed.item.id,
            )

            return processed

        summary, why_it_matters = _parse_response(response)

        if summary is None:
            logger.warning(
                "Unparsable summary response: id=%s",
                processed.item.id,
            )

            return processed

        enriched = processed.item.model_copy(
            update={
                "summary": summary,
                "why_it_matters": why_it_matters,
                "topics": processed.topics,
                "importance_score": processed.importance_score,
            },
        )

        return ProcessedItem(
            item=enriched,
            relevance_score=processed.relevance_score,
            topics=processed.topics,
            importance_score=processed.importance_score,
        )

    @staticmethod
    def _build_prompt(
        item: Article | ResearchPaper,
    ) -> str:
        """Build the prompt appropriate to the item type."""
        if isinstance(item, ResearchPaper):
            return PAPER_PROMPT.format(
                title=item.title,
                abstract=item.abstract,
            )

        return NEWS_PROMPT.format(
            title=item.title,
            content=(
                item.content or item.description or item.title
            ),
        )


def _parse_response(
    response: str,
) -> tuple[str | None, str | None]:
    """Split a model response into its two labelled parts.

    Small models drop or reword the labels often enough that a
    strict parser would throw away usable text, so an unlabelled
    response is treated as the summary.
    """
    summary_match = SUMMARY_PATTERN.search(response)
    why_match = WHY_PATTERN.search(response)

    if summary_match is None:
        text = response.strip()

        return (text or None), None

    summary = summary_match.group(1).strip()

    why_it_matters = (
        why_match.group(1).strip() if why_match else None
    )

    return (summary or None), (why_it_matters or None)
