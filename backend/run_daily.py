"""Entry point for the daily PulseX brief."""

import logging
import sys
from pathlib import Path

from backend.config.settings import Settings, get_settings
from backend.delivery.renderer import BriefRenderer
from backend.delivery.sender import (
    EmailDeliveryError,
    ResendEmailSender,
)
from backend.llm.providers.openrouter import (
    OpenRouterProvider,
)
from backend.services.brief import BriefGenerationService
from backend.services.digest import create_digest_pipeline
from backend.services.summarization import (
    SummarizationService,
)
from backend.storage.seen_store import JSONSeenStore


logger = logging.getLogger(__name__)


def run(settings: Settings | None = None) -> int:
    """Collect, summarize, and email today's brief."""
    config = settings or get_settings()

    seen_store = JSONSeenStore(
        path=Path(config.seen_store_path),
    )

    pipeline = create_digest_pipeline(seen_store=seen_store)

    result = pipeline.run()

    for failure in result.failures:
        logger.warning(
            "Source failed: source=%s error=%s",
            failure.source,
            failure.error,
        )

    provider = OpenRouterProvider(
        api_key=config.openrouter_api_key,
        model=config.openrouter_model,
    )

    logger.info(
        "Using OpenRouter model: %s",
        config.openrouter_model or "free model fallback list",
    )

    # Summarize only what the brief will carry. Items arrive
    # ranked, and generate() keeps this same number, so
    # summarizing the whole day spent a call per item on
    # content the email then discarded.
    selected = result.processed.items[: config.max_brief_items]

    summarized = SummarizationService(
        provider=provider,
    ).summarize(selected)

    if not summarized:
        # Nothing cleared the filters. Mark what we looked at so
        # it is not reconsidered, but do not send an empty email.
        logger.info("No new content today, skipping send")

        seen_store.mark_seen(result.considered)

        return 0

    brief = BriefGenerationService(
        provider=provider,
        max_items=config.max_brief_items,
    ).generate(summarized)

    renderer = BriefRenderer()

    sender = ResendEmailSender(
        api_key=config.resend_api_key,
        sender=config.email_from,
    )

    try:
        sender.send(
            recipient=config.email_to,
            subject=renderer.render_subject(brief),
            html=renderer.render(brief, summarized),
        )
    except EmailDeliveryError:
        # Nothing is marked seen, so today's content is offered
        # again on the next run rather than being lost.
        logger.exception("Could not send the daily brief")

        return 1

    seen_store.mark_seen(result.considered)

    logger.info(
        "Daily brief complete: items=%d",
        len(summarized),
    )

    return 0


def main() -> int:
    """Configure logging and run the daily brief."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    return run()


if __name__ == "__main__":
    sys.exit(main())
