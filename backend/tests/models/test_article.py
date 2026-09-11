from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.models import Article, Topic


def create_article(**overrides: object) -> Article:
    timestamp = datetime.now(timezone.utc)

    data: dict[str, object] = {
        "id": "article-001",
        "title": "New AI Model Released",
        "source": "Example AI",
        "source_url": "https://example.com",
        "url": "https://example.com/article",
        "published_at": timestamp,
        "fetched_at": timestamp,
        "topics": [
            Topic.LLM,
            Topic.GENERATIVE_AI,
        ],
        "importance_score": 0.8,
        "content_hash": "abc123",
    }

    data.update(overrides)

    return Article(**data)


def test_article_can_be_created() -> None:
    article = create_article()

    assert article.id == "article-001"
    assert article.title == "New AI Model Released"
    assert Topic.LLM in article.topics


def test_article_defaults_are_applied() -> None:
    article = create_article()

    assert article.author is None
    assert article.description is None
    assert article.content is None
    assert article.image_url is None
    assert article.summary is None
    assert article.why_it_matters is None


def test_article_can_have_author() -> None:
    article = create_article(author="Jane Doe")

    assert article.author == "Jane Doe"


def test_article_can_have_content() -> None:
    article = create_article(
        description="An AI article.",
        content="Full article content.",
    )

    assert article.description == "An AI article."
    assert article.content == "Full article content."


def test_article_can_have_image() -> None:
    article = create_article(
        image_url="https://example.com/image.jpg",
    )

    assert str(article.image_url) == "https://example.com/image.jpg"


def test_article_importance_score_can_be_zero() -> None:
    article = create_article(importance_score=0.0)

    assert article.importance_score == 0.0


def test_article_importance_score_can_be_one() -> None:
    article = create_article(importance_score=1.0)

    assert article.importance_score == 1.0


def test_article_importance_score_cannot_exceed_one() -> None:
    with pytest.raises(ValidationError):
        create_article(importance_score=1.1)


def test_article_importance_score_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        create_article(importance_score=-0.1)


def test_article_requires_id() -> None:
    with pytest.raises(ValidationError):
        create_article(id="")


def test_article_requires_title() -> None:
    with pytest.raises(ValidationError):
        create_article(title="")


def test_article_requires_source() -> None:
    with pytest.raises(ValidationError):
        create_article(source="")


def test_article_requires_valid_source_url() -> None:
    with pytest.raises(ValidationError):
        create_article(source_url="not-a-url")


def test_article_requires_valid_url() -> None:
    with pytest.raises(ValidationError):
        create_article(url="not-a-url")


def test_article_requires_content_hash() -> None:
    with pytest.raises(ValidationError):
        create_article(content_hash="")


def test_article_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        create_article(unexpected_field="value")


def test_article_serializes_to_dict() -> None:
    article = create_article()

    data = article.model_dump()

    assert isinstance(data, dict)
    assert data["id"] == "article-001"
    assert data["title"] == "New AI Model Released"