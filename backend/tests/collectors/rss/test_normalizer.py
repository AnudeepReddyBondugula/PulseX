"""Tests for RSS entry normalization."""

from time import struct_time
from typing import Any

import pytest

from backend.collectors.rss.normalizer import (
    RSSNormalizationError,
    RSSNormalizer,
)
from backend.models import Source, SourceType


@pytest.fixture
def source() -> Source:
    """Return a test RSS source."""
    return Source(
        name="Test Source",
        feed_url="https://example.com/rss.xml",
        source_type=SourceType.NEWS,
    )


@pytest.fixture
def normalizer() -> RSSNormalizer:
    """Return a normalizer."""
    return RSSNormalizer()


def valid_entry(**overrides: Any) -> dict[str, Any]:
    """Return a minimally valid raw RSS entry."""
    entry: dict[str, Any] = {
        "title": "OpenAI releases a new model",
        "link": "https://example.com/article",
        "summary": "A short description.",
        "published_parsed": struct_time(
            (2026, 9, 15, 10, 30, 0, 0, 258, 0),
        ),
    }

    entry.update(overrides)

    return entry


class TestRequiredFields:
    """Title and link are the only fields we cannot do without."""

    def test_title_and_url_are_carried_over(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        article = normalizer.normalize(valid_entry(), source)

        assert article.title == "OpenAI releases a new model"
        assert str(article.url) == (
            "https://example.com/article"
        )

    def test_source_details_come_from_the_source(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        article = normalizer.normalize(valid_entry(), source)

        assert article.source == "Test Source"
        assert str(article.source_url) == str(source.feed_url)

    def test_missing_title_is_rejected(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry()
        del entry["title"]

        with pytest.raises(RSSNormalizationError):
            normalizer.normalize(entry, source)

    def test_blank_title_is_rejected(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        with pytest.raises(RSSNormalizationError):
            normalizer.normalize(
                valid_entry(title="   "),
                source,
            )

    def test_missing_link_is_rejected(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry()
        del entry["link"]

        with pytest.raises(RSSNormalizationError):
            normalizer.normalize(entry, source)

    def test_surrounding_whitespace_is_stripped(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        article = normalizer.normalize(
            valid_entry(title="  Padded title  "),
            source,
        )

        assert article.title == "Padded title"


class TestPublicationDate:
    """A date is required, but feeds disagree on which field."""

    def test_published_parsed_is_preferred(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        article = normalizer.normalize(valid_entry(), source)

        assert article.published_at.year == 2026
        assert article.published_at.month == 9
        assert article.published_at.day == 15
        assert article.published_at.hour == 10

    def test_updated_parsed_is_the_fallback(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry()
        del entry["published_parsed"]

        entry["updated_parsed"] = struct_time(
            (2026, 9, 14, 8, 0, 0, 0, 257, 0),
        )

        article = normalizer.normalize(entry, source)

        assert article.published_at.day == 14

    def test_dates_are_timezone_aware(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        """A naive datetime would break recency scoring."""
        article = normalizer.normalize(valid_entry(), source)

        assert article.published_at.tzinfo is not None
        assert article.fetched_at.tzinfo is not None

    def test_no_date_at_all_is_rejected(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry()
        del entry["published_parsed"]

        with pytest.raises(RSSNormalizationError):
            normalizer.normalize(entry, source)


class TestOptionalContent:
    """Everything except title, link and date is optional."""

    def test_description_comes_from_summary(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        article = normalizer.normalize(valid_entry(), source)

        assert article.description == "A short description."

    def test_content_list_is_preferred_for_body(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry()
        entry["content"] = [{"value": "The full body text."}]

        article = normalizer.normalize(entry, source)

        assert article.content == "The full body text."

    def test_body_falls_back_to_summary(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        article = normalizer.normalize(valid_entry(), source)

        assert article.content == "A short description."

    def test_author_is_optional(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        assert (
            normalizer.normalize(
                valid_entry(),
                source,
            ).author
            is None
        )

    def test_author_is_used_when_present(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        article = normalizer.normalize(
            valid_entry(author="Alice Smith"),
            source,
        )

        assert article.author == "Alice Smith"

    def test_enrichment_fields_start_empty(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        """Summaries are filled in later, by the LLM."""
        article = normalizer.normalize(valid_entry(), source)

        assert article.summary is None
        assert article.why_it_matters is None
        assert article.topics == []
        assert article.importance_score == 0.0


class TestIdentity:
    """Ids and hashes drive cross-run and in-batch dedup."""

    def test_id_is_stable_for_the_same_url(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        """The seen store depends on this being deterministic."""
        first = normalizer.normalize(valid_entry(), source)
        second = normalizer.normalize(valid_entry(), source)

        assert first.id == second.id

    def test_id_differs_between_urls(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        first = normalizer.normalize(valid_entry(), source)

        second = normalizer.normalize(
            valid_entry(link="https://example.com/other"),
            source,
        )

        assert first.id != second.id

    def test_content_hash_changes_with_content(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        first = normalizer.normalize(valid_entry(), source)

        second = normalizer.normalize(
            valid_entry(summary="Different text entirely."),
            source,
        )

        assert first.content_hash != second.content_hash


class TestImageExtraction:
    """Feeds advertise images in several incompatible places."""

    def test_media_thumbnail_is_used(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry(
            media_thumbnail=[
                {"url": "https://example.com/hero.jpg"},
            ],
        )

        article = normalizer.normalize(entry, source)

        assert str(article.image_url) == (
            "https://example.com/hero.jpg"
        )

    def test_media_content_image_is_used(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry(
            media_content=[
                {
                    "url": "https://example.com/hero.png",
                    "medium": "image",
                },
            ],
        )

        article = normalizer.normalize(entry, source)

        assert str(article.image_url) == (
            "https://example.com/hero.png"
        )

    def test_non_image_media_is_ignored(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        """A podcast enclosure is not a hero image."""
        entry = valid_entry(
            media_content=[
                {
                    "url": "https://example.com/audio.mp3",
                    "medium": "audio",
                },
            ],
        )

        article = normalizer.normalize(entry, source)

        assert article.image_url is None

    def test_image_enclosure_is_used(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry(
            enclosures=[
                {
                    "href": "https://example.com/hero.jpg",
                    "type": "image/jpeg",
                },
            ],
        )

        article = normalizer.normalize(entry, source)

        assert str(article.image_url) == (
            "https://example.com/hero.jpg"
        )

    def test_image_link_is_used(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry(
            links=[
                {
                    "href": "https://example.com/hero.webp",
                    "type": "image/webp",
                },
            ],
        )

        article = normalizer.normalize(entry, source)

        assert str(article.image_url) == (
            "https://example.com/hero.webp"
        )

    def test_inline_html_image_is_the_last_resort(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry(
            summary=(
                '<p>Text <img src="https://example.com/in.png"/>'
                "</p>"
            ),
        )

        article = normalizer.normalize(entry, source)

        assert str(article.image_url) == (
            "https://example.com/in.png"
        )

    def test_explicit_image_beats_inline_html(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        entry = valid_entry(
            media_thumbnail=[
                {"url": "https://example.com/explicit.jpg"},
            ],
            summary=(
                '<img src="https://example.com/inline.png"/>'
            ),
        )

        article = normalizer.normalize(entry, source)

        assert str(article.image_url) == (
            "https://example.com/explicit.jpg"
        )

    def test_missing_image_is_not_an_error(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        """Plenty of feeds carry no image at all."""
        article = normalizer.normalize(valid_entry(), source)

        assert article.image_url is None

    def test_relative_image_is_rejected(
        self,
        normalizer: RSSNormalizer,
        source: Source,
    ) -> None:
        """A relative path would fail HttpUrl validation."""
        entry = valid_entry(
            media_thumbnail=[{"url": "/local/hero.jpg"}],
        )

        article = normalizer.normalize(entry, source)

        assert article.image_url is None
