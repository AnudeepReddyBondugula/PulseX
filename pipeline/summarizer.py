"""
summarizer.py — Generates short summaries for news articles and papers.

Depends only on the LLMProvider interface (pipeline.llm.base) — never on a
specific vendor SDK. Swap providers by passing a different LLMProvider
instance into Summarizer(); no changes needed here.
"""

from typing import Optional

from pydantic import BaseModel

from pipeline.config import CLAUDE_MODEL, GEMINI_MODEL, get_logger, get_settings
from llm.base import LLMProvider
from llm.providers.open_router_provider import OpenRouterProvider

logger = get_logger(__name__)

NEWS_SUMMARY_PROMPT = (
    "Summarize this tech news article in 2-3 concise, plain-English lines. "
    "No preamble, no markdown, just the summary text.\n\n"
    "Title: {title}\n\nDescription: {raw_summary}"
)

PAPER_SUMMARY_PROMPT = (
    "Summarize this research paper abstract in 1-2 concise, plain-English lines. "
    "No preamble, no markdown, no jargon where a simpler word works.\n\n"
    "Title: {title}\n\nAbstract: {raw_summary}"
)


class SummaryResult(BaseModel):
    item_id: str
    summary: str
    link: str


class Summarizer:
    """
    Provider is injected via the constructor — defaults to Anthropic, but
    any LLMProvider implementation can be swapped in (tests use a fake one).
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self._provider = provider or self._build_default_provider()

    @staticmethod
    def _build_default_provider() -> LLMProvider:
        settings = get_settings()
        
        # Use OpenRouterProvider as the default provider
        # Using only free models for now, but can be changed to any other model supported by OpenRouter
        return OpenRouterProvider(api_key=settings.openrouter_api_key, model="openrouter/free")

    def summarize_news_item(self, item) -> SummaryResult:
        prompt = NEWS_SUMMARY_PROMPT.format(title=item.title, raw_summary=item.raw_summary)
        summary_text = self._provider.generate(prompt)
        logger.info("Summarized news item %s", item.id)
        return SummaryResult(item_id=item.id, summary=summary_text, link=item.link)

    def summarize_paper_item(self, item) -> SummaryResult:
        prompt = PAPER_SUMMARY_PROMPT.format(title=item.title, raw_summary=item.raw_summary)
        summary_text = self._provider.generate(prompt)
        logger.info("Summarized paper item %s", item.id)
        return SummaryResult(item_id=item.id, summary=summary_text, link=item.link)