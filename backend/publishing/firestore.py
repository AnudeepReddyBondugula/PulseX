"""Publishing briefs to Firestore for the mobile app."""

import json
import logging
from typing import Any

from backend.models import DailyBrief, ResearchPaper
from backend.services.content_processing import ProcessedItem


logger = logging.getLogger(__name__)


BRIEFS_COLLECTION = "briefs"

NEWS_KIND = "news"

PAPER_KIND = "paper"


class BriefPublishError(Exception):
    """Raised when a brief cannot be published."""


class FirestoreBriefPublisher:
    """Write each day's brief to Firestore.

    Items are embedded in the brief document rather than kept in a
    subcollection, so the app opens a day with a single read. Fifteen
    summarized items sit far inside Firestore's one megabyte document
    limit.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def publish(
        self,
        brief: DailyBrief,
        items: list[ProcessedItem],
    ) -> str:
        """Publish one brief and return its document id.

        The document id is the brief's date, so a re-run for the
        same day overwrites rather than duplicating.
        """
        document_id = brief.date.isoformat()

        payload = {
            **_brief_fields(brief),
            "items": [_item_fields(item) for item in items],
        }

        logger.info(
            "Publishing brief to Firestore: id=%s items=%d",
            document_id,
            len(items),
        )

        try:
            (
                self._client.collection(BRIEFS_COLLECTION)
                .document(document_id)
                .set(payload)
            )
        except Exception as exc:
            logger.exception(
                "Failed to publish brief: id=%s",
                document_id,
            )

            raise BriefPublishError(
                f"Failed to publish brief {document_id}"
            ) from exc

        logger.info(
            "Brief published: id=%s",
            document_id,
        )

        return document_id


def _brief_fields(brief: DailyBrief) -> dict[str, Any]:
    """Render the brief's own fields for Firestore."""
    return {
        "id": brief.id,
        "date": brief.date.isoformat(),
        "title": brief.title,
        "introduction": brief.introduction,
        "summary": brief.summary,
        "generatedAt": brief.generated_at.isoformat(),
        "articleCount": len(brief.article_ids),
        "paperCount": len(brief.paper_ids),
    }


def _item_fields(processed: ProcessedItem) -> dict[str, Any]:
    """Render one item for Firestore.

    Keys are camelCase because the app reads them directly, and
    Dart code reads better that way than with snake_case.
    """
    item = processed.item

    is_paper = isinstance(item, ResearchPaper)

    fields: dict[str, Any] = {
        "id": item.id,
        "kind": PAPER_KIND if is_paper else NEWS_KIND,
        "title": item.title,
        "url": str(item.url),
        "publishedAt": item.published_at.isoformat(),
        "summary": item.summary,
        "whyItMatters": item.why_it_matters,
        "topics": [topic.value for topic in processed.topics],
        "importanceScore": processed.importance_score,
    }

    if is_paper:
        fields["source"] = "arXiv"
        fields["authors"] = item.authors
        fields["imageUrl"] = None
    else:
        fields["source"] = item.source
        fields["authors"] = (
            [item.author] if item.author else []
        )
        fields["imageUrl"] = (
            str(item.image_url) if item.image_url else None
        )

    return fields


def create_firestore_client(service_account_json: str) -> Any:
    """Build a Firestore client from service account credentials.

    The credentials arrive as JSON in an environment variable
    rather than a file, because the only place this runs is a CI
    runner with no persistent disk.
    """
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:
        raise BriefPublishError(
            "firebase-admin is not installed",
        ) from exc

    try:
        parsed = json.loads(service_account_json)
    except ValueError as exc:
        raise BriefPublishError(
            "Firebase service account is not valid JSON",
        ) from exc

    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(
            credentials.Certificate(parsed),
        )

    return firestore.client(app)
