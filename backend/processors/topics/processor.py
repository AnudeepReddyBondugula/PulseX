"""Deterministic topic extraction."""

import re
from functools import lru_cache
from typing import Dict, List, Tuple

from backend.config.topics import TOPIC_KEYWORDS
from backend.models.topic import Topic


class TopicExtractor:
    """Extract PulseX topics using deterministic keyword matching."""

    def __init__(
        self,
        topic_keywords: dict[Topic, tuple[str, ...]] = TOPIC_KEYWORDS,
    ) -> None:
        self._topic_keywords = topic_keywords
        # Pre-compile regex patterns for all keywords to avoid recompilation
        self._compiled_patterns: Dict[Topic, List[re.Pattern]] = {}
        for topic, keywords in topic_keywords.items():
            patterns = []
            for keyword in keywords:
                normalized_keyword = keyword.lower().strip()
                if normalized_keyword:  # Skip empty keywords
                    pattern = re.compile(
                        rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)"
                    )
                    patterns.append(pattern)
            self._compiled_patterns[topic] = patterns

    def extract(
        self,
        text: str,
    ) -> list[Topic]:
        """Extract topics from text."""
        if not text:
            return []
        
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return []

        topics: list[Topic] = []

        for topic, patterns in self._compiled_patterns.items():
            # Check if any of the pre-compiled patterns match
            if any(pattern.search(normalized_text) for pattern in patterns):
                topics.append(topic)

        return topics

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text before topic matching."""
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()