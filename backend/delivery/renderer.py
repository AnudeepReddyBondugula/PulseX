"""HTML rendering for the daily brief email."""

from html import escape

from backend.models import DailyBrief, ResearchPaper
from backend.services.content_processing import ProcessedItem


BODY_STYLE = (
    "margin:0;padding:24px;background:#f5f6f8;"
    "font-family:-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    "color:#1a1a1a;line-height:1.6;"
)

CARD_STYLE = (
    "max-width:640px;margin:0 auto;background:#ffffff;"
    "border-radius:12px;padding:32px;"
)

TITLE_STYLE = (
    "margin:0 0 8px;font-size:24px;font-weight:700;"
)

INTRO_STYLE = "margin:0 0 24px;font-size:16px;color:#333333;"

SECTION_STYLE = (
    "margin:32px 0 16px;font-size:13px;font-weight:700;"
    "letter-spacing:0.08em;text-transform:uppercase;"
    "color:#6b7280;"
)

ITEM_STYLE = (
    "margin:0 0 24px;padding:0 0 24px;"
    "border-bottom:1px solid #eeeeee;"
)

LINK_STYLE = (
    "font-size:17px;font-weight:600;color:#1d4ed8;"
    "text-decoration:none;"
)

META_STYLE = (
    "margin:4px 0 8px;font-size:13px;color:#6b7280;"
)

SUMMARY_STYLE = "margin:0 0 8px;font-size:15px;"

WHY_STYLE = (
    "margin:0;font-size:14px;color:#374151;"
    "border-left:3px solid #d1d5db;padding-left:12px;"
)

FOOTER_STYLE = (
    "margin:32px 0 0;font-size:12px;color:#9ca3af;"
    "text-align:center;"
)


class BriefRenderer:
    """Render a daily brief as an email-safe HTML document.

    Styles are inline because email clients strip stylesheets,
    and every value drawn from a feed is escaped: titles and
    summaries are third-party text that often contains markup.
    """

    def render(
        self,
        brief: DailyBrief,
        items: list[ProcessedItem],
    ) -> str:
        """Render the brief and its items as HTML."""
        articles = [
            processed
            for processed in items
            if not isinstance(processed.item, ResearchPaper)
        ]

        papers = [
            processed
            for processed in items
            if isinstance(processed.item, ResearchPaper)
        ]

        sections = [
            self._render_section("In the news", articles),
            self._render_section("From arXiv", papers),
        ]

        return (
            "<!DOCTYPE html>"
            '<html lang="en"><head>'
            '<meta charset="utf-8">'
            '<meta name="viewport" '
            'content="width=device-width,initial-scale=1">'
            f"<title>{escape(brief.title)}</title>"
            f"</head><body style=\"{BODY_STYLE}\">"
            f'<div style="{CARD_STYLE}">'
            f'<h1 style="{TITLE_STYLE}">'
            f"{escape(brief.title)}</h1>"
            f'<p style="{INTRO_STYLE}">'
            f"{escape(brief.introduction)}</p>"
            f'<p style="{SUMMARY_STYLE}">'
            f"{escape(brief.summary)}</p>"
            f"{''.join(sections)}"
            f'<p style="{FOOTER_STYLE}">'
            "You are receiving this because you subscribed "
            "to the PulseX daily brief."
            "</p>"
            "</div></body></html>"
        )

    def render_subject(self, brief: DailyBrief) -> str:
        """Return the email subject line."""
        return brief.title

    def _render_section(
        self,
        heading: str,
        items: list[ProcessedItem],
    ) -> str:
        """Render one titled section, or nothing when empty."""
        if not items:
            return ""

        rendered = "".join(
            self._render_item(processed)
            for processed in items
        )

        return (
            f'<h2 style="{SECTION_STYLE}">'
            f"{escape(heading)}</h2>{rendered}"
        )

    def _render_item(
        self,
        processed: ProcessedItem,
    ) -> str:
        """Render one content item."""
        item = processed.item

        meta = self._render_meta(processed)

        summary = (
            f'<p style="{SUMMARY_STYLE}">'
            f"{escape(item.summary)}</p>"
            if item.summary
            else ""
        )

        why = (
            f'<p style="{WHY_STYLE}">'
            f"<strong>Why it matters:</strong> "
            f"{escape(item.why_it_matters)}</p>"
            if item.why_it_matters
            else ""
        )

        return (
            f'<div style="{ITEM_STYLE}">'
            f'<a href="{escape(str(item.url))}" '
            f'style="{LINK_STYLE}">{escape(item.title)}</a>'
            f"{meta}{summary}{why}"
            "</div>"
        )

    @staticmethod
    def _render_meta(processed: ProcessedItem) -> str:
        """Render the source and topic line for an item."""
        item = processed.item

        if isinstance(item, ResearchPaper):
            source = ", ".join(item.authors[:3]) or "arXiv"
        else:
            source = item.source

        topics = ", ".join(
            topic.value for topic in processed.topics
        )

        parts = [source]

        if topics:
            parts.append(topics)

        return (
            f'<p style="{META_STYLE}">'
            f"{escape(' · '.join(parts))}</p>"
        )
