import pytest
from pydantic import ValidationError

from backend.models import Source, SourceType


def create_source(**overrides: object) -> Source:
    data: dict[str, object] = {
        "name": "Example AI",
        "feed_url": "https://example.com/feed.xml",
        "source_type": SourceType.NEWS,
    }

    data.update(overrides)

    return Source(**data)


def test_source_can_be_created() -> None:
    source = create_source()

    assert source.name == "Example AI"
    assert str(source.feed_url) == "https://example.com/feed.xml"
    assert source.source_type == SourceType.NEWS
    assert source.enabled is True


def test_source_defaults_to_enabled() -> None:
    source = create_source()

    assert source.enabled is True


def test_source_can_be_disabled() -> None:
    source = create_source(enabled=False)

    assert source.enabled is False


def test_source_requires_name() -> None:
    with pytest.raises(ValidationError):
        create_source(name="")


def test_source_requires_valid_feed_url() -> None:
    with pytest.raises(ValidationError):
        create_source(feed_url="not-a-valid-url")


def test_source_requires_valid_source_type() -> None:
    with pytest.raises(ValidationError):
        create_source(source_type="invalid")


def test_source_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        create_source(unexpected_field="value")


def test_source_is_immutable() -> None:
    source = create_source()

    with pytest.raises(ValidationError):
        source.enabled = False