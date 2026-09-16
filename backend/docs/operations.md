# Operations

How PulseX runs in production, and what has actually gone wrong.

## The two workflows

### `ci.yml` — tests

Triggers on pushes to `develop` and `master`, and on every pull request.
Checkout → install uv → `uv sync --extra dev` → `uv run pytest -q`. Around ten
seconds.

`concurrency` with `cancel-in-progress: true`: a superseded run tells you nothing
once a newer commit exists. Permissions are `contents: read` — CI has no reason
to write to the repository.

### `daily-brief.yml` — the actual product

```yaml
on:
  schedule:
    - cron: "0 0 * * *"   # 00:00 UTC = 05:30 IST
  workflow_dispatch:
```

Checkout → install uv → install dependencies → send the brief → commit the seen
store.

Three details worth knowing:

- **GitHub cron is UTC only**, and scheduled runs are routinely delayed five to
  fifteen minutes under load. Treat 05:30 as approximate.
- **`concurrency` uses `cancel-in-progress: false`**, the opposite of CI. Two
  overlapping runs would race for `data/seen_items.json`, and cancelling one
  mid-send could leave it half-written.
- **`permissions: contents: write`** is required, because the run commits the
  seen store back.

Scheduled workflows only fire from the default branch. A change to
`daily-brief.yml` on `develop` does nothing until it reaches `master`.

## Secrets

Set at **Settings → Secrets and variables → Actions**:

`OPENROUTER_API_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_TO`.

Optional: `OPENROUTER_MODEL`, `MAX_BRIEF_ITEMS`, `SEEN_STORE_PATH` — all have
working defaults.

## State between runs

Runners are ephemeral, so the seen store is committed back to the repository:

```bash
if [[ -z "$(git status --porcelain data/seen_items.json)" ]]; then
  echo "Seen store unchanged, nothing to commit."
  exit 0
fi
git add data/seen_items.json
git commit -m "chore: record delivered items for $(date -u +%Y-%m-%d)"
git push
```

A daily automated commit in the history is the cost of needing no
infrastructure. If that becomes irritating, the `SeenStore` protocol is narrow
enough to back with Firestore instead — `filter_new` and `mark_seen` are the
whole interface.

**To force a resend**, delete `data/seen_items.json` on `master`. The next run
recollects everything and rebuilds it.

## Rate limits

OpenRouter free tier: **20 requests per minute, 50 per day** on an account that
has never bought credits. A default run costs 16 (15 items + 1 opening).

This is why `run_daily` slices to `max_brief_items` before summarizing, and why
`OpenRouterProvider` stops trying after every model has been refused. An earlier
version did neither and made roughly 575 requests in one run, every one of them
doomed.

## Reading a run

Trigger manually from the Actions tab, then read the "Send the daily brief"
step. Healthy output looks like:

```
INFO Starting collection: sources=11 queries=1
INFO Completed collection: articles=... papers=... failures=0
INFO Filtered seen content: total=... new=...
INFO Processing collected content: items=...
INFO Digest run complete: ranked=... duplicates=... irrelevant=...
INFO Using OpenRouter model: free model fallback list
INFO Summarizing content: items=15
INFO Generating brief: articles=10 papers=5
INFO Sending brief: recipient=*** subject=PulseX Daily Brief — ...
INFO Brief sent: message_id=...
INFO Saved seen store: path=data/seen_items.json records=...
INFO Daily brief complete: items=15
```

**A green run does not mean a good brief.** Both early failures finished green
and delivered email, because degradation is deliberate. Two signals catch it:

- **Duration.** Real LLM calls take minutes. A send step finishing in under a
  minute means the model calls are failing fast.
- **`Model unavailable, trying the next one`.** Any occurrence means the model
  list is being walked, which should not happen once the auto-router resolves.

## Things that have actually broken

### Every OpenRouter call returned 404

**Symptom.** Green run, email delivered, no summaries anywhere, generic
fallback opening. Send step finished in 17 seconds.

**Cause.** Three pinned free slugs had moved to paid and two no longer existed.

**Diagnosis.** The provider recorded only the status code, discarding the body.
A retired slug and a data-policy rejection both return 404, so the log could not
distinguish them. Fixed by carrying the server's message into the error, which
immediately revealed `"This model is unavailable for free. The paid version is
available"`.

**Fix.** Route through `openrouter/free` so rotation stops mattering.

**Lesson.** Log the body, not just the status. Two hours of guessing became one
run's worth of certainty.

### A paper crashed the whole run

**Symptom.** `AttributeError: 'ResearchPaper' object has no attribute
'content_hash'`, then the same for `source`.

**Cause.** `Deduplicator` and `RankingProcessor` were written against `Article`
and reached for fields only it has.

**Why tests missed it.** Every processor test used articles exclusively. 187
tests passed while the pipeline could not process a single arXiv paper.

**Lesson.** When a function takes a union type, test every member of the union.
Mixed batches are now covered.

### Feeds could not be verified before deploying

All 11 URLs were unreachable from the development sandbox. They went to
production unverified — and all 11 worked, but that was luck.

What made it safe was `CollectionService` recording a failure per source rather
than aborting. Design for the parts you cannot test.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `ValidationError` at startup | A secret missing or empty |
| `openrouter_model must be...` | A paid slug configured |
| Every model 404s | Privacy settings, or the slug list is stale |
| `429` from OpenRouter | Daily 50-request cap spent |
| Resend rejects the send | `EMAIL_FROM` domain not verified |
| Email arrives with no summaries | LLM calls failing; check for `Model unavailable` |
| "No new content today" | Everything already in the seen store |
| Nothing at 05:30 IST | Scheduled runs are delayed; also check the workflow is on `master` |
| Email not in the inbox | Check spam — `resend.dev` is a shared domain with no reputation |
