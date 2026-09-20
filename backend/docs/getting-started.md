# Getting started

From a fresh clone to a passing test suite, then to a brief in your own inbox.

## Requirements

- **Python 3.11 or newer** (`requires-python = ">=3.11"`). The code uses
  `StrEnum`, `X | Y` unions and `datetime.UTC`, none of which exist in 3.10.
- **[uv](https://docs.astral.sh/uv/)** for dependency management. Everything
  below assumes it; `pip install -e .` works too if you prefer.

## Setup

```bash
git clone https://github.com/AnudeepReddyBondugula/PulseX.git
cd PulseX
uv sync --extra dev
```

That creates `.venv/` and installs four runtime dependencies plus pytest.

## Run the tests

```bash
uv run pytest
```

You should see **204 passed** in well under a second. `pyproject.toml` points
`testpaths` at `backend/tests`, so a bare `pytest` finds everything.

The suite needs no network, no API keys and no fixtures on disk. If it is slow
or tries to reach the internet, something is wrong.

Useful variants:

```bash
uv run pytest backend/tests/processors     # one area
uv run pytest -k ranking                   # one topic
uv run pytest -x -q                        # stop at the first failure
uv run pytest -vv                          # see every test name
```

## Configuration

Runtime needs four secrets. Copy the template:

```bash
cp .env.example .env
```

| Variable | Where to get it |
| --- | --- |
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `RESEND_API_KEY` | [resend.com/api-keys](https://resend.com/api-keys) |
| `EMAIL_FROM` | An address on a domain verified with Resend |
| `EMAIL_TO` | Wherever you want the brief |

Two things that catch people out:

**`EMAIL_FROM` cannot be a personal Gmail address.** Resend verifies a sending
domain through DNS records, which you cannot add to `gmail.com`. Without a
domain of your own, use `onboarding@resend.dev`, which delivers only to the
address on your Resend account.

**Free OpenRouter models require permissive privacy settings.** Free capacity
comes from providers who may log prompts. If your account forbids that, every
free model returns 404. The toggles are at
[openrouter.ai/settings/privacy](https://openrouter.ai/settings/privacy).

`Settings` is strict: a missing or empty secret raises at startup rather than
halfway through a run.

## Run it for real

```bash
uv run python -m backend.run_daily
```

This does the whole thing: fetches 11 feeds and arXiv, filters and ranks,
summarizes the top 15, renders HTML, and sends one email. Expect it to take a
few minutes — the LLM calls dominate.

It writes `data/seen_items.json` on success. Delete that file if you want to
resend the same content while experimenting.

Exit codes: `0` on success or when there was nothing new to send, `1` when the
email could not be delivered.

## Poke at the pieces

Every component is usable on its own, which is the fastest way to understand
one. Ranking, with no network:

```python
from datetime import UTC, datetime, timedelta
from backend.models import Article
from backend.processors.ranking.processor import RankingProcessor

now = datetime.now(UTC)
article = Article(
    id="1", title="OpenAI releases a new model", source="OpenAI",
    source_url="https://openai.com", url="https://openai.com/1",
    published_at=now - timedelta(hours=6), fetched_at=now,
    content_hash="h1",
)
print(RankingProcessor().score(article, relevance_score=0.8, now=now))
```

The whole deterministic pipeline, still with no network:

```python
from backend.processors.deduplication.processor import Deduplicator
from backend.processors.ranking.processor import RankingProcessor
from backend.processors.relevance.processor import RelevanceProcessor
from backend.processors.topics.processor import TopicExtractor
from backend.services.content_processing import ContentProcessingService

service = ContentProcessingService(
    Deduplicator(), RelevanceProcessor(), TopicExtractor(), RankingProcessor(),
)
result = service.process([article])
for item in result.items:
    print(f"{item.importance_score:.3f}  {item.item.title}  {item.topics}")
```

Summarization and the brief without spending API calls — pass a fake provider:

```python
from backend.services.summarization import SummarizationService

class StubProvider:
    def generate(self, prompt: str) -> str:
        return "SUMMARY: Something happened.\nWHY IT MATTERS: It is relevant."

print(SummarizationService(StubProvider()).summarize(result.items))
```

Anything satisfying `LLMProvider` works here. That is the whole point of the
interface, and it is how the tests avoid the network.

## Project layout at a glance

```
PulseX/
├── backend/            All the code. See architecture.md.
├── .github/workflows/
│   ├── ci.yml          Tests on push and pull request
│   └── daily-brief.yml The 05:37 IST run
├── data/               seen_items.json, written by runs (not in a fresh clone)
├── .env.example        Template for the four secrets
└── pyproject.toml      Dependencies, pytest config
```

## Next

Read [the pipeline walkthrough](pipeline.md) to follow one item from feed to
inbox, or [architecture](architecture.md) for the layering and the reasoning
behind it.
