"""Tests for arXiv Atom XML parsing."""

import pytest

from backend.collectors.arxiv.parser import (
    ArxivParser,
    ArxivParsingError,
)


SAMPLE_ARXIV_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed
    xmlns="http://www.w3.org/2005/Atom"
    xmlns:arxiv="http://arxiv.org/schemas/atom"
>
    <entry>
        <id>https://arxiv.org/abs/2601.12345</id>

        <updated>2026-01-15T12:00:00Z</updated>

        <published>2026-01-10T08:30:00Z</published>

        <title>
            A New Approach to Artificial Intelligence
        </title>

        <summary>
            This paper presents a new approach to AI research.
        </summary>

        <author>
            <name>Alice Smith</name>
        </author>

        <author>
            <name>Bob Jones</name>
        </author>

        <category term="cs.AI"/>
        <category term="cs.LG"/>

        <arxiv:primary_category
            term="cs.AI"
        />

        <link
            rel="alternate"
            type="text/html"
            href="https://arxiv.org/abs/2601.12345"
        />

        <link
            title="pdf"
            type="application/pdf"
            href="https://arxiv.org/pdf/2601.12345"
        />
    </entry>
</feed>
"""


def test_parse_extracts_entry_fields() -> None:
    parser = ArxivParser()

    entries = parser.parse(SAMPLE_ARXIV_XML)

    assert len(entries) == 1

    entry = entries[0]

    assert entry.id_url == "https://arxiv.org/abs/2601.12345"
    assert entry.title == "A New Approach to Artificial Intelligence"
    assert entry.summary == (
        "This paper presents a new approach to AI research."
    )

    assert entry.authors == [
        "Alice Smith",
        "Bob Jones",
    ]

    assert entry.published == "2026-01-10T08:30:00Z"
    assert entry.updated == "2026-01-15T12:00:00Z"

    assert entry.categories == [
        "cs.AI",
        "cs.LG",
    ]

    assert entry.primary_category == "cs.AI"

    assert entry.abstract_url == (
        "https://arxiv.org/abs/2601.12345"
    )

    assert entry.pdf_url == (
        "https://arxiv.org/pdf/2601.12345"
    )


def test_parse_normalizes_whitespace() -> None:
    xml = """\
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>https://arxiv.org/abs/2601.12345</id>
            <updated>2026-01-15T12:00:00Z</updated>
            <published>2026-01-10T08:30:00Z</published>

            <title>
                A title with
                extra whitespace
            </title>

            <summary>
                A summary with
                multiple lines.
            </summary>
        </entry>
    </feed>
    """

    parser = ArxivParser()

    entries = parser.parse(xml)

    assert entries[0].title == (
        "A title with extra whitespace"
    )

    assert entries[0].summary == (
        "A summary with multiple lines."
    )


def test_parse_handles_missing_optional_fields() -> None:
    xml = """\
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>https://arxiv.org/abs/2601.12345</id>
            <updated>2026-01-15T12:00:00Z</updated>
            <published>2026-01-10T08:30:00Z</published>
            <title>Minimal Paper</title>
            <summary>A minimal summary.</summary>
        </entry>
    </feed>
    """

    parser = ArxivParser()

    entries = parser.parse(xml)

    entry = entries[0]

    assert entry.authors == []
    assert entry.categories == []
    assert entry.primary_category is None
    assert entry.abstract_url is None
    assert entry.pdf_url is None


def test_parse_raises_for_malformed_xml() -> None:
    parser = ArxivParser()

    malformed_xml = "<feed><entry><title>Broken"

    with pytest.raises(ArxivParsingError):
        parser.parse(malformed_xml)


def test_parse_raises_when_required_field_is_missing() -> None:
    xml = """\
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>https://arxiv.org/abs/2601.12345</id>
            <updated>2026-01-15T12:00:00Z</updated>
            <published>2026-01-10T08:30:00Z</published>
            <summary>A summary.</summary>
        </entry>
    </feed>
    """

    parser = ArxivParser()

    with pytest.raises(ArxivParsingError):
        parser.parse(xml)