"""Tests for AI summarization."""

from unittest.mock import Mock

from backend.llm.base import LLMProviderError
from backend.models import Article, ResearchPaper, Topic
from backend.services.content_processing import ProcessedItem
from backend.services.summarization import (
    SummarizationService,
)


def create_processed_article() -> ProcessedItem:
    """Create a processed news article."""
    return ProcessedItem(
        item=Article(
            id="1",
            title="New model released",
            source="Test Source",
            source_url="https://example.com",
            url="https://example.com/1",
            published_at="2026-01-01T00:00:00Z",
            fetched_at="2026-01-01T01:00:00Z",
            description="A model was released.",
            content_hash="hash-1",
        ),
        relevance_score=0.8,
        topics=[Topic.LLM],
        importance_score=0.7,
    )


def create_processed_paper() -> ProcessedItem:
    """Create a processed research paper."""
    return ProcessedItem(
        item=ResearchPaper(
            id="2601.1",
            arxiv_id="2601.1",
            title="On scaling laws",
            authors=["Alice Smith"],
            abstract="We study scaling behaviour.",
            url="https://arxiv.org/abs/2601.1",
            published_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            categories=["cs.LG"],
        ),
        relevance_score=0.9,
        topics=[Topic.MACHINE_LEARNING],
        importance_score=0.8,
    )


def test_summarize_fills_both_fields() -> None:
    provider = Mock()

    provider.generate.return_value = (
        "SUMMARY: A model shipped.\n"
        "WHY IT MATTERS: It is faster."
    )

    service = SummarizationService(provider=provider)

    result = service.summarize([create_processed_article()])

    assert result[0].item.summary == "A model shipped."
    assert result[0].item.why_it_matters == "It is faster."


def test_summarize_preserves_processing_metadata() -> None:
    provider = Mock()

    provider.generate.return_value = "SUMMARY: Text."

    service = SummarizationService(provider=provider)

    result = service.summarize([create_processed_article()])

    assert result[0].topics == [Topic.LLM]
    assert result[0].importance_score == 0.7
    assert result[0].item.topics == [Topic.LLM]


def test_papers_use_the_plain_language_prompt() -> None:
    provider = Mock()

    provider.generate.return_value = "SUMMARY: Text."

    service = SummarizationService(provider=provider)

    service.summarize([create_processed_paper()])

    prompt = provider.generate.call_args.args[0]

    assert "non-specialist" in prompt
    assert "We study scaling behaviour." in prompt


def test_provider_failure_keeps_the_item() -> None:
    provider = Mock()

    provider.generate.side_effect = LLMProviderError(
        "rate limited",
    )

    service = SummarizationService(provider=provider)

    result = service.summarize([create_processed_article()])

    assert len(result) == 1
    assert result[0].item.summary is None


def test_one_failure_does_not_stop_the_rest() -> None:
    provider = Mock()

    provider.generate.side_effect = [
        LLMProviderError("rate limited"),
        "SUMMARY: Papers summary.",
    ]

    service = SummarizationService(provider=provider)

    result = service.summarize(
        [
            create_processed_article(),
            create_processed_paper(),
        ],
    )

    assert result[0].item.summary is None
    assert result[1].item.summary == "Papers summary."


def test_unlabelled_response_becomes_the_summary() -> None:
    provider = Mock()

    provider.generate.return_value = "Just plain text."

    service = SummarizationService(provider=provider)

    result = service.summarize([create_processed_article()])

    assert result[0].item.summary == "Just plain text."
    assert result[0].item.why_it_matters is None
