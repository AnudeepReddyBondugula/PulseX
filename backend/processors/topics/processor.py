"""Deterministic topic extraction."""

import re

from backend.config.topics import TOPIC_KEYWORDS
from backend.models.topic import Topic


class TopicExtractor:
    """Extract PulseX topics using deterministic keyword matching."""

    def __init__(
        self,
        topic_keywords: dict[Topic, tuple[str, ...]] = TOPIC_KEYWORDS,
    ) -> None:
        self._topic_keywords = topic_keywords

    def extract(
        self,
        text: str,
    ) -> list[Topic]:
        """Extract topics from text."""
        normalized_text = self._normalize_text(text)

        if not normalized_text:
            return []

        topics: list[Topic] = []

        for topic, keywords in self._topic_keywords.items():
            if any(
                self._contains_keyword(
                    normalized_text,
                    keyword,
                ) for keyword in keywords):
                topics.append(topic)

        return topics

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text before topic matching."""
        text = text.lower()
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def _contains_keyword(
        text: str,
        keyword: str,
    ) -> bool:
        """Check whether a keyword occurs as a phrase."""
        normalized_keyword = keyword.lower().strip()

        if not normalized_keyword:
            return False

        pattern = (
            rf"(?<!\w)"
            rf"{re.escape(normalized_keyword)}"
            rf"(?!\w)"
        )

        return re.search(
            pattern,
            text,
        ) is not None