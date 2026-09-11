from enum import StrEnum


class Topic(StrEnum):
    """Supported AI topics in PulseX."""

    LLM = "LLM"
    GENERATIVE_AI = "Generative AI"
    AI_AGENTS = "AI Agents"
    MACHINE_LEARNING = "Machine Learning"
    DEEP_LEARNING = "Deep Learning"
    COMPUTER_VISION = "Computer Vision"
    NLP = "NLP"
    MULTIMODAL_AI = "Multimodal AI"
    ROBOTICS = "Robotics"
    AI_SAFETY = "AI Safety"
    AI_INFRASTRUCTURE = "AI Infrastructure"
    AI_RESEARCH = "AI Research"
    AI_HARDWARE = "AI Hardware"