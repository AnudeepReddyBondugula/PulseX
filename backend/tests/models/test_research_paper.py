from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.models import ResearchPaper, Topic


def create_research_paper(**overrides: object) -> ResearchPaper:
    timestamp = datetime.now(timezone.utc)

    data: dict[str, object] = {
        "id": "paper-001",
        "arxiv_id": "2501.12345",
        "title": "A Study of AI Agents",
        "authors": [
            "Alice Smith",
            "Bob Smith",
        ],
        "abstract": "This paper studies AI agents.",
        "url": "https://arxiv.org/abs/2501.12345",
        "published_at": timestamp,
        "updated_at": timestamp,
        "categories": [
            "cs.AI",
            "cs.LG",
        ],
        "topics": [
            Topic.AI_AGENTS,
            Topic.LLM,
        ],
        "importance_score": 0.9,
        "summary": "The paper studies AI agents.",
        "why_it_matters": (
            "It provides useful insights into agent architectures."
        ),
    }

    data.update(overrides)

    return ResearchPaper(**data)


def test_research_paper_can_be_created() -> None:
    paper = create_research_paper()

    assert paper.id == "paper-001"
    assert paper.arxiv_id == "2501.12345"
    assert paper.title == "A Study of AI Agents"


def test_research_paper_has_authors() -> None:
    paper = create_research_paper()

    assert len(paper.authors) == 2
    assert "Alice Smith" in paper.authors


def test_research_paper_has_categories() -> None:
    paper = create_research_paper()

    assert "cs.AI" in paper.categories
    assert "cs.LG" in paper.categories


def test_research_paper_has_topics() -> None:
    paper = create_research_paper()

    assert Topic.AI_AGENTS in paper.topics
    assert Topic.LLM in paper.topics


def test_research_paper_defaults_collections_to_empty_lists() -> None:
    paper = create_research_paper(
        authors=[],
        categories=[],
        topics=[],
    )

    assert paper.authors == []
    assert paper.categories == []
    assert paper.topics == []


def test_research_paper_summary_is_optional() -> None:
    paper = create_research_paper(
        summary=None,
        why_it_matters=None,
    )

    assert paper.summary is None
    assert paper.why_it_matters is None


def test_research_paper_requires_arxiv_id() -> None:
    with pytest.raises(ValidationError):
        create_research_paper(arxiv_id="")


def test_research_paper_requires_title() -> None:
    with pytest.raises(ValidationError):
        create_research_paper(title="")


def test_research_paper_requires_abstract() -> None:
    with pytest.raises(ValidationError):
        create_research_paper(abstract="")


def test_research_paper_requires_valid_url() -> None:
    with pytest.raises(ValidationError):
        create_research_paper(url="not-a-url")


def test_research_paper_importance_score_cannot_exceed_one() -> None:
    with pytest.raises(ValidationError):
        create_research_paper(importance_score=1.1)


def test_research_paper_importance_score_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        create_research_paper(importance_score=-0.1)


def test_research_paper_serializes_to_dict() -> None:
    paper = create_research_paper()

    data = paper.model_dump()

    assert isinstance(data, dict)
    assert data["id"] == "paper-001"
    assert data["arxiv_id"] == "2501.12345"