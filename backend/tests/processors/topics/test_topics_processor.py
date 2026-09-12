"""Tests for topic extraction."""

from backend.models.topic import Topic
from backend.processors.topics.processor import TopicExtractor


def test_extracts_llm_topic() -> None:
    extractor = TopicExtractor()

    topics = extractor.extract(
        "The new LLM improves reasoning performance."
    )

    assert Topic.LLM in topics


def test_extracts_multiple_topics() -> None:
    extractor = TopicExtractor()

    topics = extractor.extract(
        """
        The new multimodal AI agent uses an LLM
        for computer vision and natural language
        processing.
        """
    )

    assert Topic.LLM in topics
    assert Topic.AI_AGENTS in topics
    assert Topic.MULTIMODAL_AI in topics
    assert Topic.COMPUTER_VISION in topics
    assert Topic.NLP in topics


def test_returns_empty_list_when_no_topics_match() -> None:
    extractor = TopicExtractor()

    topics = extractor.extract(
        "A new football stadium opened today."
    )

    assert topics == []


def test_matching_is_case_insensitive() -> None:
    extractor = TopicExtractor()

    topics = extractor.extract(
        "NEW LARGE LANGUAGE MODEL RELEASED"
    )

    assert Topic.LLM in topics


def test_matching_handles_extra_whitespace() -> None:
    extractor = TopicExtractor()

    topics = extractor.extract(
        "New    machine   learning   model"
    )

    assert Topic.MACHINE_LEARNING in topics


def test_short_keyword_does_not_match_inside_word() -> None:
    extractor = TopicExtractor()

    topics = extractor.extract(
        "The company said it would build a railway."
    )

    assert Topic.LLM not in topics
    assert Topic.NLP not in topics


def test_keyword_matching_uses_phrase_boundaries() -> None:
    extractor = TopicExtractor()

    topics = extractor.extract(
        "This is about robotics systems."
    )

    assert Topic.ROBOTICS in topics


def test_empty_text_returns_empty_list() -> None:
    extractor = TopicExtractor()

    assert extractor.extract("") == []


def test_whitespace_only_text_returns_empty_list() -> None:
    extractor = TopicExtractor()

    assert extractor.extract("   \n\t ") == []
    
    
def test_custom_topic_configuration() -> None:
    extractor = TopicExtractor(
        topic_keywords={
            Topic.LLM: (
                "custom language model",
            ),
        },
    )

    topics = extractor.extract(
        "A custom language model was released."
    )

    assert topics == [Topic.LLM]