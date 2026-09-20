# PulseX

Daily AI-curated digest of tech news and arXiv research from trusted sources.

PulseX collects AI news from 11 RSS feeds and research papers from arXiv, filters
and ranks them with explainable heuristics, summarizes the best of them with an
LLM, and emails one brief every morning at 05:37 IST.

Research papers are explained in plain language, on the assumption the reader is
curious rather than a specialist.

## How it works

```
RSS feeds ─┐                                                        ┌→ email
           ├─→ collect ─→ filter ─→ rank ─→ summarize ─→ brief ──────┼→ Firestore → app
arXiv API ─┘               (seen)          (LLM)                    └→ FCM → notification
```

Filtering and ranking are deterministic: keyword matching, exponential recency
decay, per-source quality priors. No model decides what you read, so every
decision can be explained by pointing at a number. The LLM is used only to write
prose about items already selected.

## Quick start

```bash
git clone https://github.com/AnudeepReddyBondugula/PulseX.git
cd PulseX
uv sync --extra dev
uv run pytest                          # 204 tests, offline, about a second

cp .env.example .env                   # then fill in four secrets
uv run python -m backend.run_daily     # collect, summarize, send
```

You will need an [OpenRouter](https://openrouter.ai/keys) key and a
[Resend](https://resend.com/api-keys) key. Both have usable free tiers;
[getting started](backend/docs/getting-started.md) covers the two setup details
that catch people out.

## Documentation

Full documentation lives in **[`backend/docs/`](backend/docs/README.md)**.

| | |
| --- | --- |
| [Getting started](backend/docs/getting-started.md) | Setup, tests, running components offline |
| [Architecture](backend/docs/architecture.md) | Layers, module map, design decisions |
| [The pipeline](backend/docs/pipeline.md) | One run, stage by stage |
| [Configuration](backend/docs/configuration.md) | Every secret and tuning knob |
| [Mobile setup](backend/docs/mobile-setup.md) | Firebase, running the app, Play Store release |
| [Contributing](backend/docs/contributing.md) | Conventions and recipes |
| [Operations](backend/docs/operations.md) | Workflows, rate limits, what has broken |
| [Mathematical theory](backend/docs/PulseX_Content_Processing_Mathematical_Theory.md) | The scoring formulas in full |

## Project status

v0.1 is running: collection, processing, summarization and email delivery, on a
daily schedule with tests on every push.

Planned next: cross-run storage in Firestore rather than a committed JSON file,
and a Flutter mobile client in a later release.

## Stack

**Backend:** Python 3.11+, pydantic, httpx, feedparser, firebase-admin.
OpenRouter for summarization, Resend for email, Firestore and FCM for the app,
GitHub Actions for scheduling.

**App:** Flutter, with Firebase core, Firestore, Auth and Messaging.
