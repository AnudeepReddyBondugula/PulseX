from backend.models import Topic


def test_topic_values_are_strings() -> None:
    assert Topic.LLM.value == "LLM"
    assert Topic.GENERATIVE_AI.value == "Generative AI"
    assert Topic.AI_AGENTS.value == "AI Agents"


def test_topic_values_are_unique() -> None:
    values = [topic.value for topic in Topic]

    assert len(values) == len(set(values))


def test_expected_topics_exist() -> None:
    expected_topics = {
        "LLM",
        "Generative AI",
        "AI Agents",
        "Machine Learning",
        "Deep Learning",
        "Computer Vision",
        "NLP",
        "Multimodal AI",
        "Robotics",
        "AI Safety",
        "AI Infrastructure",
        "AI Research",
        "AI Hardware",
    }

    actual_topics = {topic.value for topic in Topic}

    assert actual_topics == expected_topics