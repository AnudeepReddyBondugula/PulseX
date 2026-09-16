"""Daily brief generation."""

import logging
from datetime import UTC, datetime

from backend.llm.base import LLMProvider, LLMProviderError
from backend.models import Article, DailyBrief, ResearchPaper
from backend.services.content_processing import ProcessedItem


logger = logging.getLogger(__name__)


DEFAULT_MAX_ITEMS = 15

BRIEF_PROMPT = """\
You are writing the opening of PulseX, a daily AI news and research
digest. Below are today's selected items, most important first.

Reply in exactly this format, with no preamble and no markdown:
INTRODUCTION: <2 sentences welcoming the reader and naming the day's
main theme>
SUMMARY: <3-4 sentences drawing out the through-line across today's
items>

Today's items:
{items}
"""

INTRODUCTION_PATTERN = "INTRODUCTION:"

SUMMARY_PATTERN = "SUMMARY:"


class BriefGenerationService:
    """Assemble the daily brief from ranked content."""

    def __init__(
        self,
        provider: LLMProvider,
        max_items: int = DEFAULT_MAX_ITEMS,
    ) -> None:
        self._provider = provider
        self._max_items = max_items

    def generate(
        self,
        items: list[ProcessedItem],
        *,
        now: datetime | None = None,
    ) -> DailyBrief:
        """Build the brief for one day's ranked content."""
        generated_at = now or datetime.now(UTC)

        selected = items[: self._max_items]

        articles = [
            processed.item
            for processed in selected
            if isinstance(processed.item, Article)
        ]

        papers = [
            processed.item
            for processed in selected
            if isinstance(processed.item, ResearchPaper)
        ]

        logger.info(
            "Generating brief: articles=%d papers=%d",
            len(articles),
            len(papers),
        )

        introduction, summary = self._write_opening(
            selected,
            articles=len(articles),
            papers=len(papers),
        )

        brief_date = generated_at.date()

        return DailyBrief(
            id=f"pulsex-{brief_date.isoformat()}",
            date=brief_date,
            title=(
                "PulseX Daily Brief — "
                f"{brief_date:%B %d, %Y}"
            ),
            introduction=introduction,
            article_ids=[article.id for article in articles],
            paper_ids=[paper.id for paper in papers],
            generated_at=generated_at,
            summary=summary,
        )

    def _write_opening(
        self,
        selected: list[ProcessedItem],
        *,
        articles: int,
        papers: int,
    ) -> tuple[str, str]:
        """Write the brief's opening, falling back if needed.

        A brief that lists today's items is still worth sending
        when the model is unavailable, so a provider failure
        falls back to deterministic text rather than aborting.
        """
        fallback = _fallback_opening(
            articles=articles,
            papers=papers,
        )

        if not selected:
            return fallback

        prompt = BRIEF_PROMPT.format(
            items=_format_items(selected),
        )

        try:
            response = self._provider.generate(prompt)
        except LLMProviderError:
            logger.exception(
                "Could not generate brief opening",
            )

            return fallback

        introduction, summary = _parse_opening(response)

        return (
            introduction or fallback[0],
            summary or fallback[1],
        )


def _format_items(selected: list[ProcessedItem]) -> str:
    """Render the selected items for the prompt."""
    lines = []

    for processed in selected:
        item = processed.item

        kind = (
            "PAPER"
            if isinstance(item, ResearchPaper)
            else "NEWS"
        )

        lines.append(
            f"- [{kind}] {item.title}"
            f"{f': {item.summary}' if item.summary else ''}"
        )

    return "\n".join(lines)


def _parse_opening(
    response: str,
) -> tuple[str | None, str | None]:
    """Split the model response into introduction and summary."""
    upper = response.upper()

    intro_at = upper.find(INTRODUCTION_PATTERN)
    summary_at = upper.find(SUMMARY_PATTERN)

    if intro_at == -1 or summary_at == -1:
        return None, None

    introduction = response[
        intro_at + len(INTRODUCTION_PATTERN) : summary_at
    ].strip()

    summary = response[
        summary_at + len(SUMMARY_PATTERN) :
    ].strip()

    return (introduction or None), (summary or None)


def _fallback_opening(
    *,
    articles: int,
    papers: int,
) -> tuple[str, str]:
    """Deterministic opening used when the model is unavailable."""
    if not articles and not papers:
        return (
            "No new AI news or research cleared today's filters.",
            "PulseX found nothing new to report today.",
        )

    return (
        "Here is your daily digest of AI news and research.",
        (
            f"Today's brief collects {articles} news "
            f"{_plural(articles, 'article')} and {papers} "
            f"research {_plural(papers, 'paper')}."
        ),
    )


def _plural(count: int, noun: str) -> str:
    """Return the noun matching the count."""
    return noun if count == 1 else f"{noun}s"
