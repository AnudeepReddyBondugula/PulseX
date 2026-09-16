# Contributing

Conventions this codebase follows, and recipes for the changes people most
often want to make.

## Workflow

Work happens on `develop` and reaches `master` through a pull request.

```bash
git checkout develop
git pull origin develop
# ... change things ...
uv run pytest
git commit
git push -u origin develop
```

CI runs the suite on every push and pull request. Merges to `master` use a merge
commit, matching the existing history.

`master` is what the daily workflow runs from, so anything unmerged is not in
production.

## Code conventions

These are observed throughout; match them rather than your own habits.

**Narrow lines.** Arguments and collection literals are wrapped one per line,
generously. The existing files are the reference.

**Docstrings on every public class and method**, imperative mood, one line where
one line does. Where a decision is non-obvious, the docstring says *why*:

```python
def mark_seen(self, items, *, now=None) -> None:
    """Record items as delivered and persist the store.

    Call this only once delivery has succeeded: an item marked
    seen is never offered again, so marking before a failed send
    would drop it permanently.
    """
```

**Comments explain reasoning, not mechanics.** If a line needs a comment to say
what it does, rename something instead.

**Keyword-only arguments** for anything a caller could confuse:
`def score(self, item, *, relevance_score, now=None)`.

**Frozen dataclasses for results**, pydantic models for domain types.
`ProcessedItem`, `RankingResult` and `CollectionResult` are all
`@dataclass(frozen=True)`.

**Constructor injection.** A component that needs a collaborator takes it as a
constructor argument. Nothing constructs its own dependencies except
`create_digest_pipeline()` and `run_daily.run()`.

**Custom exceptions per boundary.** `RSSCollectionError`,
`ArxivParsingError`, `EmailDeliveryError`, `LLMProviderError`. Catch the
specific one; never a bare `except Exception` unless you are logging and
re-raising.

## Testing

204 tests, all offline, whole suite under a second. Keep it that way.

**Never hit the network.** Pass mocks into constructors. HTTP is tested by
patching `httpx.Client`:

```python
def patch_post(*responses):
    client = Mock()
    client.post.side_effect = responses
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    return client

with patch("httpx.Client", return_value=client):
    ...
```

**Test names state the behaviour**, not the method:
`test_failed_delivery_does_not_mark_items_seen`, not `test_run_daily_2`.

**Where a test encodes a decision, say so in a docstring.** These are the tests
that stop someone "simplifying" a deliberate choice:

```python
def test_failed_delivery_does_not_mark_items_seen(...):
    """Marking after a failed send would lose the day's content."""
```

**Test every member of a union type.** `Article | ResearchPaper` means both, in
isolation and mixed. Two production crashes came from processors tested only
with articles. Mixed-batch tests now exist in the deduplication and ranking
suites; keep them passing.

**Mirror the source tree.** `backend/services/brief.py` is tested by
`backend/tests/services/test_brief_service.py`.

## Recipes

### Add a news source

1. Append a `Source` to `RSS_SOURCES` in `config/sources.py`.
2. Add the same `name` to `SOURCE_QUALITY_SCORES` in `config/source_quality.py`.
   Miss this and it silently scores 0.5.
3. Run the suite. Nothing pins the count, but `test_sources.py` validates shape.

You cannot verify the URL offline. The first live run's logs will tell you — a
bad URL appears as a `CollectionFailure` and costs nothing else.

### Add a topic

1. Add the member to `Topic` in `models/topic.py`.
2. Add its keywords to `TOPIC_KEYWORDS` in `config/topics.py`.
3. Add its arXiv categories to `TOPIC_ARXIV_CATEGORIES` in `config/arxiv.py`.

Step 3 is enforced: `test_categories_cover_every_topic` asserts the mapping
covers every enum member.

### Add an LLM provider

1. New file in `llm/providers/`.
2. Subclass `LLMProvider`, implement `generate(self, prompt: str) -> str`.
3. Raise `LLMProviderError` on failure — callers catch exactly that. Subclass it
   for retryable or fall-through cases, as `OpenRouterProvider` does.
4. Wire it in `run_daily.run()`.

Nothing above `llm/` names a vendor, so callers need no changes.

### Replace the seen store

Implement `filter_new(items) -> list[ContentItem]` and `mark_seen(items) -> None`.
That is the entire `SeenStore` protocol. Pass your implementation to
`create_digest_pipeline(seen_store=...)`.

Whatever you build, keep the invariant: **the pipeline filters, the caller
marks, and only after delivery succeeds.**

### Change the email's appearance

`delivery/renderer.py`. Styles are inline constants at module level because
email clients strip stylesheets. Escape everything drawn from a feed —
`html.escape` is already applied to every interpolated value, and the escaping
test will catch a regression.

To preview without sending, render to a file and open it:

```python
html = BriefRenderer().render(brief, items)
Path("preview.html").write_text(html)
```

### Adjust what gets picked

Almost always configuration rather than code:

- More or less inclusive → `threshold` in `config/relevance.py`
- More news-driven → lower `recency_half_life_hours` in `config/ranking.py`
- Trust a publisher more → `config/source_quality.py`
- A longer brief → `MAX_BRIEF_ITEMS`, minding the 50-request daily cap

## Before opening a pull request

- `uv run pytest` passes
- New behaviour has a test; new *decisions* have a test with a docstring
- Both `Article` and `ResearchPaper` paths covered if you touched shared code
- No network calls in tests
- Config changes reflected in `.env.example` and these docs

Describe *why* in the pull request body, not just what. The diff shows what.
