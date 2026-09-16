# The pipeline

One run of PulseX, stage by stage. Read this alongside `backend/run_daily.py`,
which is short and does exactly what this describes.

## Stage 1 — Collection

**`services/collection.py` · `collectors/`**

`CollectionService.collect()` runs every configured source and returns one
`CollectionResult`.

### RSS

For each of the 11 feeds in `config/sources.py`:

1. `RSSCollector.collect(source)` fetches with `feedparser` and returns raw
   entry dicts. A disabled source returns `[]` without a request. A feed that
   fails to parse *and* yields no entries raises `RSSCollectionError`.
2. `RSSNormalizer.normalize(entry, source)` maps each entry to an `Article`:
   required `title` and `link`, optional description and content, a publication
   date from `published_parsed` or `updated_parsed`, a SHA-256 `content_hash`
   over title + URL + content, and an id that is the SHA-256 of the URL.
3. `RSSIngestionService.ingest(source)` joins the two.

A single bad entry does not sink the feed. `_normalize_entry` catches both
`RSSNormalizationError` (a missing field) and pydantic's `ValidationError` (a
relative or malformed link that fails `HttpUrl`), logs it, and skips that entry.

That second case is easy to miss: normalization can succeed and the `Article`
constructor still reject the result.

### arXiv

One combined query covers all 11 categories:

```
(cat:cs.AI OR cat:cs.AR OR cat:cs.CL OR ... OR cat:stat.ML)
  AND submittedDate:[202609150000 TO 202609160000]
```

1. `ArxivQueryConfig.build_search_query()` assembles that string, including the
   24-hour window. Without the window, sorting by submission date returns the
   newest papers but not necessarily *recent* ones, and consecutive days overlap
   heavily.
2. `ArxivCollector.collect(config)` GETs `export.arxiv.org/api/query`.
3. `ArxivParser.parse(xml)` walks the Atom response into `RawArxivEntry` objects.
4. `ArxivNormalizer.normalize(entry)` produces a `ResearchPaper`.

One request rather than eleven, because arXiv asks clients to space out calls.

### Failure handling

A source that raises is recorded as a `CollectionFailure(source, error)` and the
loop continues. A dead feed costs its own items and nothing else — which is how
the first live run survived with all 11 feed URLs unverified.

## Stage 2 — The seen store

**`storage/seen_store.py`**

`JSONSeenStore.filter_new(items)` drops anything whose id appears in
`data/seen_items.json`.

Without this, every run re-delivers yesterday's content: `Deduplicator` only
compares items *within a single batch*, so it cannot know what last run sent.

The store prunes records older than 60 days on write, so the file cannot grow
without bound, and falls back to empty on a missing or corrupt file — a bad
store costs one day of repeats rather than the whole run.

**It is never written here.** See stage 7.

## Stage 3 — Deterministic processing

**`services/content_processing.py` · `processors/`**

Four processors in a fixed order. `PulseX_Content_Processing_Mathematical_Theory.md`
has the formulas; this is the shape.

### Deduplication

An item is a duplicate if it matches an earlier one in the batch on any of:
content hash, canonical URL (query strings and fragments stripped), or
normalized title. First occurrence wins.

Only `Article` carries a precomputed `content_hash` from its collector;
`ResearchPaper` does not, so the processor hashes its fields instead. Reaching
for `item.content_hash` unconditionally used to crash every run containing a
paper.

### Relevance

Keyword matching against 23 AI terms, scored separately over title and body and
combined at **0.7 title / 0.3 body** — a term in the headline says more than one
buried in paragraph nine. Items scoring below **0.2** are dropped.

Title and body are read differently per type: an `Article` has
`description`/`content`, a `ResearchPaper` has `abstract`. Both branches are
guarded by `isinstance`.

### Topics

Binary matching of each of the 13 `Topic` values against its keyword list
(72 keywords total). An item can carry several topics or none; topics are
labels for the reader, not filters.

### Ranking

A weighted sum, bounded to `[0, 1]`:

| Component | Weight | How it is computed |
| --- | --- | --- |
| Recency | 0.25 | Exponential decay, 48-hour half-life |
| Relevance | 0.30 | Carried over from the relevance stage |
| Source quality | 0.20 | Per-publisher prior, 0.5 for unknown sources |
| Significance | 0.25 | Title terms like "release" or "benchmark", +0.2 for papers |

Exponential decay rather than linear means a 12-hour-old item is still strong,
a two-day-old item has halved, and nothing ever goes negative.

Papers have no `source` field, so ranking maps them to the `"arXiv"` entry in
`SOURCE_QUALITY_SCORES` (0.95). Publisher names in that table must match
`config/sources.py` exactly or the item silently scores as unknown.

Output is `ProcessedContent(items, duplicates, irrelevant)`, items sorted by
importance descending.

## Stage 4 — Summarization

**`services/summarization.py`**

```python
selected = result.processed.items[: config.max_brief_items]
```

**Only the top 15 are summarized.** The brief keeps that many anyway, and free
OpenRouter accounts are capped at 50 requests a day — summarizing all ~115
relevant items would exhaust the quota before the email was sent.

One call per item. Articles get a news prompt; papers get a prompt that asks for
plain language and no jargon, because the reader is not a specialist. Both ask
for:

```
SUMMARY: ...
WHY IT MATTERS: ...
```

The parser is deliberately forgiving. Small models reword or drop labels often
enough that a strict parser would throw away usable text, so an unlabelled
response is kept whole as the summary.

A failure on one item logs and returns that item unchanged, `summary` still
`None`. The renderer omits empty fields, so the brief simply carries a bare
title and link for that entry.

## Stage 5 — Brief generation

**`services/brief.py`**

`BriefGenerationService.generate()` splits the selected items into articles and
papers, then makes one more LLM call for the opening — an introduction and a
summary drawing the through-line across the day.

If that call fails or comes back unparsable, `_fallback_opening()` supplies
deterministic text ("Today's brief collects 10 news articles and 5 research
papers"). A brief listing the day's items is still worth sending.

An empty day short-circuits: no LLM call, and `DailyBrief` still gets non-empty
`introduction` and `summary`, which its schema requires.

## Stage 6 — Rendering and delivery

**`delivery/`**

`BriefRenderer.render(brief, items)` produces a single HTML document. Two
constraints shape it:

- **Styles are inline.** Email clients strip `<style>` blocks.
- **Every interpolated value is escaped** with `html.escape`. Titles and
  summaries are third-party text that frequently contains markup.

Sections ("In the news", "From arXiv") are omitted when empty rather than
rendered as empty headings.

`ResendEmailSender.send()` POSTs to the Resend API and returns the message id. A
rejected request or an unreachable API raises `EmailDeliveryError`, and a 200
response without an `id` is also an error — a send we cannot confirm is not a
send.

## Stage 7 — Marking seen

```python
seen_store.mark_seen(result.considered)
```

The last thing a successful run does.

If delivery raised, `run_daily.run()` returns `1` **without marking anything**,
so the next run offers the same content again. Marking before the send would
mean a rejected email silently destroys that day's brief, permanently.

The GitHub workflow then commits `data/seen_items.json` back to the repository,
which is how state survives between runs on ephemeral runners.

## Running the whole thing without the network

Useful when you want to see the output of a change. Pass a stub provider and
build the items by hand — see the examples in
[getting-started.md](getting-started.md#poke-at-the-pieces).
