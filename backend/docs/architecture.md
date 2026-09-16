# Architecture

How PulseX is put together, and why it is put together that way.

## What the system does

Once a day, PulseX collects AI news from RSS feeds and research papers from
arXiv, decides which of it is worth reading, summarizes the best of it with an
LLM, and emails one brief to one reader.

```
RSS feeds ─┐
           ├─→ collection ─→ seen store ─→ processing ─→ summarization ─→ brief ─→ email
arXiv API ─┘                  (filter)      (rank)        (LLM)          (LLM)    (Resend)
```

## The layers

Every module lives in one of six layers. Dependencies point downward only: a
layer may import from the layers below it, never from the ones above.

| Layer | Package | Responsibility |
| --- | --- | --- |
| Entry point | `backend/run_daily.py` | Wires everything together for one run |
| Services | `backend/services/` | Orchestration: sequencing other components |
| Delivery | `backend/delivery/` | Rendering and sending the email |
| Processors | `backend/processors/` | Deterministic scoring and filtering |
| Collectors | `backend/collectors/` | Fetching and normalizing external content |
| Foundations | `backend/models/`, `backend/config/`, `backend/llm/`, `backend/storage/` | Shared types, configuration, interfaces, persistence |

If you find yourself wanting a processor to import a service, something has
gone sideways — the dependency belongs the other way round.

## Module map

```
backend/
├── run_daily.py              Entry point. Wires and sequences one daily run.
│
├── models/                   Pydantic domain types. No behaviour, no I/O.
│   ├── article.py            Article — a news item from an RSS feed
│   ├── research_paper.py     ResearchPaper — a paper from arXiv
│   ├── daily_brief.py        DailyBrief — the assembled brief
│   ├── source.py             Source, SourceType — a configured feed
│   └── topic.py              Topic — the 13 subject labels
│
├── collectors/               Turning the outside world into models.
│   ├── rss/
│   │   ├── collector.py      RSSCollector — fetches a feed (feedparser)
│   │   ├── normalizer.py     RSSNormalizer — raw entry → Article
│   │   └── service.py        RSSIngestionService — joins the two
│   └── arxiv/
│       ├── collector.py      ArxivCollector — queries the API (httpx)
│       ├── parser.py         ArxivParser — Atom XML → RawArxivEntry
│       ├── normalizer.py     ArxivNormalizer — entry → ResearchPaper
│       └── service.py        ArxivIngestionService — joins the three
│
├── processors/               Deterministic decisions. No I/O, no network.
│   ├── deduplication/        Deduplicator — drops repeats within a batch
│   ├── relevance/            RelevanceProcessor — is this about AI?
│   ├── topics/               TopicExtractor — which topics apply?
│   └── ranking/              RankingProcessor — how important is this?
│
├── llm/                      The only place a model vendor is named.
│   ├── base.py               LLMProvider (ABC), LLMProviderError
│   └── providers/
│       └── openrouter.py     OpenRouterProvider — the one implementation
│
├── services/                 Orchestration. Each one sequences, none fetch.
│   ├── collection.py         CollectionService — every source, one result
│   ├── content_processing.py ContentProcessingService — the four processors
│   ├── digest.py             DigestPipeline — collection → processing
│   ├── summarization.py      SummarizationService — fills in AI summaries
│   └── brief.py              BriefGenerationService — assembles DailyBrief
│
├── delivery/                 Getting it to a human.
│   ├── renderer.py           BriefRenderer — DailyBrief → HTML
│   └── sender.py             ResendEmailSender — HTML → inbox
│
├── storage/
│   └── seen_store.py         JSONSeenStore — what has already been sent
│
├── config/                   Values, not logic.
│   ├── settings.py           Settings — secrets from the environment
│   ├── sources.py            RSS_SOURCES — the 11 feeds
│   ├── arxiv.py              Topic → arXiv category mapping, query building
│   ├── relevance.py          Keywords, threshold, title/body weights
│   ├── ranking.py            The four importance weights, decay half-life
│   ├── source_quality.py     Per-publisher quality priors
│   └── topics.py             Topic → keyword mapping (72 keywords)
│
└── tests/                    Mirrors the tree above. 204 tests.
```

## Four ideas that explain most of the code

### 1. Deterministic first, AI second

Deduplication, relevance, topics and ranking are pure functions over the
content: keyword matching, hashing, arithmetic. No model is consulted. Only
after that pipeline has chosen the top items does an LLM get involved, and only
to write prose.

This means the expensive, flaky, rate-limited part of the system touches
fifteen items a day instead of two thousand, and every filtering decision can be
explained by pointing at a number. `PulseX_Content_Processing_Mathematical_Theory.md`
sets out the formulas in full.

### 2. Degrade, don't crash

A daily product that fails completely when one dependency misbehaves is worse
than one that arrives slightly thinner. So:

- One unreachable feed becomes a `CollectionFailure`; the other ten still run.
- One malformed RSS entry is skipped; the rest of the feed still normalizes.
- One failed summarization leaves that item unsummarized; the brief still sends.
- A total LLM outage falls back to deterministic text; the brief still sends.

The exception is email delivery. If the send fails the run exits non-zero,
because there is no partial version of "the reader got it".

### 3. Nothing is marked seen until it is delivered

`DigestPipeline.run()` filters through the seen store but never writes to it.
Only `run_daily.py`, after `sender.send()` returns, calls `mark_seen()`.

An item marked seen is never offered again. Marking before the send would mean
a failed email silently destroys that day's content. This ordering is enforced
by a test named `test_failed_delivery_does_not_mark_items_seen`.

### 4. Constructor injection everywhere

No service constructs its own collaborators. `ContentProcessingService` is
handed four processors; `SummarizationService` is handed a provider. The wiring
happens in exactly two places: `create_digest_pipeline()` and `run_daily.run()`.

This is why the tests are fast and hermetic — every test passes mocks into a
constructor rather than patching module globals.

## Data flow in detail

```
1. CollectionService.collect()
      RSSIngestionService.ingest(source)   × 11 feeds  → list[Article]
      ArxivIngestionService.ingest(query)  × 1 query   → list[ResearchPaper]
      failures recorded per source, never raised
   → CollectionResult(articles, papers, failures)

2. JSONSeenStore.filter_new(items)
   → only items not delivered on a previous run

3. ContentProcessingService.process(items)
      Deduplicator.deduplicate()      → unique, duplicates
      RelevanceProcessor.filter()     → relevant, irrelevant
      TopicExtractor.extract()        → topics per item
      RankingProcessor.rank()         → sorted by importance, descending
   → ProcessedContent(items, duplicates, irrelevant)

4. run_daily takes the top MAX_BRIEF_ITEMS (15) only
      SummarizationService.summarize() → one LLM call per item,
                                         fills summary + why_it_matters

5. BriefGenerationService.generate()  → one more LLM call for the opening
   → DailyBrief

6. BriefRenderer.render()             → HTML, inline styles, everything escaped
   ResendEmailSender.send()           → Resend API

7. JSONSeenStore.mark_seen(considered) → only now, only on success
```

Step 4 matters more than it looks. Everything collected gets *processed*, but
only the fifteen items that will actually appear get *summarized*. Free-tier
OpenRouter accounts are capped at 50 requests a day; summarizing everything
would exhaust the quota before the email went out.

## Where to make common changes

| You want to | Go to |
| --- | --- |
| Add a news source | `config/sources.py`, plus `config/source_quality.py` |
| Cover a new arXiv area | `config/arxiv.py` — `TOPIC_ARXIV_CATEGORIES` |
| Change what counts as relevant | `config/relevance.py` |
| Change what ranks highly | `config/ranking.py` |
| Add a topic label | `models/topic.py`, `config/topics.py`, `config/arxiv.py` |
| Change the email's look | `delivery/renderer.py` |
| Reword the summaries | `services/summarization.py` — the prompts |
| Swap LLM vendor | New file in `llm/providers/`, implement `LLMProvider` |
| Swap the seen store for a database | New class satisfying the `SeenStore` protocol |

Note how many of those are config rather than code. That is deliberate.

## Further reading

- [Getting started](getting-started.md) — set it up and run it
- [The pipeline](pipeline.md) — a stage-by-stage walkthrough
- [Configuration](configuration.md) — every knob and what it does
- [Operations](operations.md) — workflows, secrets, and what has broken before
- [Contributing](contributing.md) — conventions and how to add things
- [Mathematical theory](PulseX_Content_Processing_Mathematical_Theory.md) — the scoring formulas
