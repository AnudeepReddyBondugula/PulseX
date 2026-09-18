# PulseX documentation

Everything a new contributor needs, in the order worth reading it.

## Start here

**[Getting started](getting-started.md)** — clone, install, run the tests, run a
brief. Includes snippets for exercising individual components offline.

**[Architecture](architecture.md)** — the layers, the module map, the four ideas
that explain most of the design decisions, and a table of where to go to make
common changes.

## Going deeper

**[The pipeline](pipeline.md)** — one run stage by stage, from feed to inbox.
Read alongside `backend/run_daily.py`.

**[Configuration](configuration.md)** — every secret and every tuning knob, what
it does, and what happens if you change it.

**[Mobile setup](mobile-setup.md)** — the Flutter app: Firebase project, the
steps only the account owner can do, running it, and releasing to the Play
Store.

**[Mathematical theory](PulseX_Content_Processing_Mathematical_Theory.md)** —
the formal treatment of deduplication, relevance, topics and importance, with
notation, worked examples and the model's stated limitations.

## Working on it

**[Contributing](contributing.md)** — code and test conventions, plus recipes
for adding a source, a topic or an LLM provider.

**[Operations](operations.md)** — the two workflows, secrets, rate limits, how
to read a run, and a record of what has actually broken in production.

## Orientation in one page

PulseX collects AI news from 11 RSS feeds and research papers from arXiv, filters
and ranks them with explainable heuristics, summarizes the top 15 with an LLM,
and emails one brief every morning at 05:30 IST.

The shape of the system:

```
collection → seen store → deterministic processing → AI enrichment → delivery
```

Three things that explain most of the code:

1. **Deterministic first, AI second.** All filtering and ranking is arithmetic
   over keyword matches. The LLM only writes prose, and only for items already
   chosen. This keeps decisions explainable and keeps the expensive, rate-limited
   part of the system small.

2. **Degrade rather than crash.** A dead feed, a malformed entry, a failed
   summarization, even a total LLM outage — each costs its own piece and nothing
   more. The one exception is email delivery, where partial success is not a
   thing.

3. **Nothing is marked delivered until it is delivered.** The pipeline filters
   through the seen store but never writes to it; only a successful send does.
   Otherwise a rejected email would destroy that day's content permanently.

## Quick reference

| | |
| --- | --- |
| Python | 3.11+ |
| Dependencies | `feedparser`, `httpx`, `pydantic`, `pydantic-settings` |
| Tests | 204, offline, under a second |
| Run the suite | `uv run pytest` |
| Run a brief | `uv run python -m backend.run_daily` |
| Schedule | `0 0 * * *` UTC = 05:30 IST |
| Topics | 13 |
| RSS sources | 11 |
| arXiv categories | 11, one combined query, 24-hour window |
| Items per brief | 15 (`MAX_BRIEF_ITEMS`) |
| LLM | OpenRouter, free models only |
| Email | Resend |
