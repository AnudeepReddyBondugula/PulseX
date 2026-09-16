# Configuration

Two kinds of configuration: **secrets**, which come from the environment and
differ per deployment, and **tuning**, which lives in Python files under
`backend/config/` and is the same for everyone.

## Secrets — `config/settings.py`

`Settings` is a pydantic-settings model read from the environment, or from a
`.env` file when running locally. In CI these are repository secrets.

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | yes | — | Must be non-empty |
| `RESEND_API_KEY` | yes | — | Must be non-empty |
| `EMAIL_FROM` | yes | — | Must be a Resend-verified domain |
| `EMAIL_TO` | yes | — | Any address |
| `OPENROUTER_MODEL` | no | unset | Unset uses the free fallback list |
| `MAX_BRIEF_ITEMS` | no | `15` | Items in the brief *and* LLM calls per run |
| `SEEN_STORE_PATH` | no | `data/seen_items.json` | Where delivered ids go |

Missing secrets fail at construction, not mid-run. That is deliberate: a run
that dies after fetching 2,000 items but before sending has wasted everything.

### The paid-model guard

`_reject_paid_models` refuses any `OPENROUTER_MODEL` that is neither
`openrouter/free` nor suffixed `:free`:

```
openrouter_model must be 'openrouter/free' or a free model ending in ':free'
```

The project runs on an account with no credits. A paid slug should fail before
the run rather than at billing time. If you ever add credits, relax this
validator rather than working around it.

### `MAX_BRIEF_ITEMS` is not free

Each item is one LLM call. Free OpenRouter accounts get **50 requests a day**.
At the default of 15 a run costs 16 calls (15 items + 1 opening), leaving
headroom for a retry or a manual run. Raising it to 40 would put a single run
near the cap.

## Content sources — `config/sources.py`

`RSS_SOURCES` holds 11 `Source` entries: OpenAI, Anthropic, Google DeepMind,
Google AI, Meta AI, Microsoft Research, Hugging Face, TechCrunch AI, MIT
Technology Review AI, Ars Technica AI, The Verge AI.

```python
Source(
    name="OpenAI",
    feed_url="https://openai.com/news/rss.xml",
    source_type=SourceType.NEWS,
    enabled=True,          # default; False skips it without a request
)
```

Feed URLs are validated as `HttpUrl` at import, but never checked for
*reachability* until a run. A moved feed shows up as a `CollectionFailure` in
the logs, not as a crash.

**When adding a source, add it to `source_quality.py` too.** Names must match
exactly; an unlisted publisher scores 0.5 rather than its real quality.

## arXiv — `config/arxiv.py`

`TOPIC_ARXIV_CATEGORIES` maps each `Topic` to arXiv categories. The union is
flattened into `ARXIV_CATEGORIES` — 11 unique categories — and combined into one
OR query.

| Topic | Categories |
| --- | --- |
| LLM, NLP | `cs.CL` |
| Generative AI, Machine Learning | `cs.LG`, `stat.ML` |
| AI Agents | `cs.MA` |
| Deep Learning | `cs.NE` |
| Computer Vision, Multimodal AI | `cs.CV` |
| Robotics | `cs.RO` |
| AI Safety | `cs.CY` |
| AI Infrastructure | `cs.DC` |
| AI Research | `cs.AI` |
| AI Hardware | `cs.AR` |

Other knobs:

- `ARXIV_LOOKBACK_HOURS = 24` — the `submittedDate` window
- `ARXIV_MAX_RESULTS = 100` — per query, capped at 100 by `ArxivQueryConfig`
- `sort_by` / `sort_order` — submission date, descending

A config with `lookback_hours=None` sends the bare query with no date filter,
which is what the collector tests rely on.

## Relevance — `config/relevance.py`

```python
keywords      = 23 AI terms
threshold     = 0.2    # below this, the item is dropped
title_weight  = 0.7
body_weight   = 0.3
```

Raising `threshold` makes the brief stricter and shorter. Lowering it lets more
general tech news through.

The title/body split reflects that a keyword in the headline is a much stronger
signal than one in the ninth paragraph.

## Ranking — `config/ranking.py`

```python
recency_weight           = 0.25
relevance_weight         = 0.30
source_quality_weight    = 0.20
significance_weight      = 0.25
recency_half_life_hours  = 48.0
```

The four weights sum to 1.0. Nothing enforces that — each is independently
bounded `[0, 1]` — but the final score is clamped to `[0, 1]`, so weights
summing above 1 will flatten everything near the ceiling and destroy the
ordering. Keep the sum at 1.

`recency_half_life_hours` is the interesting dial. At 48 hours, a day-old item
retains ~71% of its recency score and a two-day-old item exactly 50%. Drop it to
24 for a more news-driven brief; raise it to 96 to let good older work linger.

## Source quality — `config/source_quality.py`

Per-publisher priors, `0.0`–`1.0`, with unknown sources defaulting to `0.5`:

- **1.00** — OpenAI, Anthropic, Google AI, Google DeepMind, Microsoft Research, Meta AI
- **0.95** — NVIDIA, Hugging Face, arXiv
- **0.90** — MIT Technology Review AI
- **0.85** — Ars Technica AI
- **0.80** — TechCrunch AI, The Verge AI, VentureBeat AI

`"arXiv"` is special: research papers have no `source` field, so
`_item_source()` maps every paper to that key.

The prior encodes "a primary-source announcement usually matters more than
coverage of it". It is a judgment call, and a reasonable thing to disagree with.

## Topics — `config/topics.py` and `models/topic.py`

13 topics, 72 keywords. Adding one means touching three files:

1. `models/topic.py` — the enum member
2. `config/topics.py` — its keywords
3. `config/arxiv.py` — its arXiv categories

A test asserts `set(TOPIC_ARXIV_CATEGORIES) == set(Topic)`, so forgetting step 3
fails the suite rather than silently dropping coverage.

## LLM models — `llm/providers/openrouter.py`

```python
AUTO_FREE_MODEL = "openrouter/free"

FREE_MODELS = (
    AUTO_FREE_MODEL,
    "openai/gpt-oss-20b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
)
```

The auto-router comes first because it resolves to whatever is free *at request
time*. The named slugs are only a backstop.

This ordering was learned the hard way: an earlier version pinned five specific
free slugs, three of which had silently moved to paid and two of which no longer
existed. Every call 404'd and two briefs went out with no summaries at all. A
hand-maintained list of free models goes stale; the auto-router does not.

Also here:

- `MAX_ATTEMPTS = 3` with exponential backoff (2s, 4s)
- `RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}` — retried
- `MODEL_UNAVAILABLE_STATUS_CODES = {400, 403, 404}` — falls through to the next model
- Everything else fails immediately

## Seen store — `storage/seen_store.py`

```python
DEFAULT_STORE_PATH = Path("data/seen_items.json")
DEFAULT_PRUNE_AFTER_DAYS = 60
```

60 days is comfortably longer than any feed's republication window, so a pruned
record cannot come back as a false "new" item.
