"""
test_summarizer.py — Unit tests for summarizer.py

Run with: pytest tests/test_summarizer.py
Uses a fake LLMProvider — no vendor SDK involved, proving summarizer.py
is genuinely provider-agnostic.
"""

from types import SimpleNamespace

from pipeline.llm.base import LLMProvider
from pipeline.summarizer import Summarizer


class FakeProvider(LLMProvider):
    """Records every prompt it was called with and returns a fixed response."""

    def __init__(self, response_text="fake summary"):
        self.response_text = response_text
        self.calls = []

    def generate(self, prompt: str, max_tokens: int = 200) -> str:
        self.calls.append((prompt, max_tokens))
        return self.response_text


def _fake_item(item_id="abc123", title="Title", link="https://example.com/a", raw_summary="Some text"):
    return SimpleNamespace(id=item_id, title=title, link=link, raw_summary=raw_summary)


def test_summarize_news_item_returns_result():
    provider = FakeProvider("News summary here.")
    summarizer = Summarizer(provider=provider)

    result = summarizer.summarize_news_item(_fake_item())

    assert result.summary == "News summary here."
    assert result.item_id == "abc123"
    assert result.link == "https://example.com/a"


def test_summarize_news_item_uses_correct_max_tokens():
    provider = FakeProvider()
    summarizer = Summarizer(provider=provider)

    summarizer.summarize_news_item(_fake_item())

    _, max_tokens = provider.calls[0]
    assert max_tokens == 200


def test_summarize_paper_item_returns_result():
    provider = FakeProvider("Paper summary here.")
    summarizer = Summarizer(provider=provider)

    result = summarizer.summarize_paper_item(_fake_item())

    assert result.summary == "Paper summary here."


def test_summarize_paper_item_uses_correct_max_tokens():
    provider = FakeProvider()
    summarizer = Summarizer(provider=provider)

    summarizer.summarize_paper_item(_fake_item())

    _, max_tokens = provider.calls[0]
    assert max_tokens == 150


def test_prompt_includes_item_title_and_content():
    provider = FakeProvider()
    summarizer = Summarizer(provider=provider)

    summarizer.summarize_news_item(_fake_item(title="Big Tech News", raw_summary="Details here"))

    prompt, _ = provider.calls[0]
    assert "Big Tech News" in prompt
    assert "Details here" in prompt