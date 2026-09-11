from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from backend.models import DailyBrief


def create_daily_brief(**overrides: object) -> DailyBrief:
    data: dict[str, object] = {
        "id": "brief-2026-09-11",
        "date": date(2026, 9, 11),
        "title": "PulseX Morning Brief",
        "introduction": (
            "Here are today's most important AI developments."
        ),
        "article_ids": [
            "article-001",
            "article-002",
        ],
        "paper_ids": [
            "paper-001",
        ],
        "generated_at": datetime.now(timezone.utc),
        "summary": (
            "Today's briefing covers major AI developments."
        ),
    }

    data.update(overrides)

    return DailyBrief(**data)


def test_daily_brief_can_be_created() -> None:
    brief = create_daily_brief()

    assert brief.id == "brief-2026-09-11"
    assert brief.title == "PulseX Morning Brief"


def test_daily_brief_contains_article_ids() -> None:
    brief = create_daily_brief()

    assert len(brief.article_ids) == 2
    assert "article-001" in brief.article_ids
    assert "article-002" in brief.article_ids


def test_daily_brief_contains_paper_ids() -> None:
    brief = create_daily_brief()

    assert len(brief.paper_ids) == 1
    assert "paper-001" in brief.paper_ids


def test_daily_brief_can_have_no_articles() -> None:
    brief = create_daily_brief(article_ids=[])

    assert brief.article_ids == []


def test_daily_brief_can_have_no_papers() -> None:
    brief = create_daily_brief(paper_ids=[])

    assert brief.paper_ids == []


def test_daily_brief_requires_title() -> None:
    with pytest.raises(ValidationError):
        create_daily_brief(title="")


def test_daily_brief_requires_introduction() -> None:
    with pytest.raises(ValidationError):
        create_daily_brief(introduction="")


def test_daily_brief_requires_summary() -> None:
    with pytest.raises(ValidationError):
        create_daily_brief(summary="")


def test_daily_brief_requires_id() -> None:
    with pytest.raises(ValidationError):
        create_daily_brief(id="")


def test_daily_brief_serializes_to_dict() -> None:
    brief = create_daily_brief()

    data = brief.model_dump()

    assert isinstance(data, dict)
    assert data["id"] == "brief-2026-09-11"