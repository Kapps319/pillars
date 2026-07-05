# Adding a new source

Every data source is a `SourceAdapter` (see `backend/app/sources/base.py`).
The pipeline only ever sees normalized `RawPost` objects, so a new source is
drop-in: implement the class, register it, done — classification, scoring,
dedupe, jobs and the UI all pick it up automatically.

## Ground rules

- **Public data + official APIs only.** No login-walled scraping, no ToS
  violations, respect robots.txt and rate limits.
- **Never crash the job.** Raise `SourceError` for transient failures; report
  missing credentials via `available()` / `required_keys` so the job runner
  logs and skips you.

## 1. Implement the adapter

`backend/app/sources/hackernews_source.py`:

```python
import httpx

from app.sources.base import RawPost, SearchFilters, SourceAdapter, SourceError


class HackerNewsSource(SourceAdapter):
    key = "hackernews"                 # unique — used in campaign.sources
    name = "Hacker News"
    description = "Algolia HN search API (public, keyless)."
    required_keys: list[str] = []      # env vars you need, e.g. ["HN_API_KEY"]
    enabled_by_default = True          # False for paid/risky sources

    def available(self) -> bool:
        return True                    # check your keys here if you have any

    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        try:
            response = httpx.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={"query": query, "tags": "comment", "hitsPerPage": filters.limit},
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceError(f"HN API error: {exc}") from exc

        return [
            RawPost(
                source_key=self.key,
                external_id=hit["objectID"],           # stable id → dedupe
                content=(hit.get("comment_text") or "")[:8000],
                author=hit.get("author"),
                url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
            )
            for hit in response.json().get("hits", [])
            if hit.get("comment_text")
        ]
```

Notes:

- `external_id` must be stable — leads are deduped on
  `(campaign, source_key, external_id)`.
- `filters` gives you the campaign's `location`, `date_from`, `date_to` and
  `limit`; use whatever your API supports.
- If your source needs API keys: read them from `Settings`
  (add fields in `app/core/config.py`, document them in `.env.example`), list
  their env-var names in `required_keys`, and return `False` from
  `available()` when they're missing. The job will report
  `{"skipped": "missing keys: ..."}` instead of failing.

## 2. Register it

In `backend/app/sources/registry.py`:

```python
from app.sources.hackernews_source import HackerNewsSource

adapters: list[SourceAdapter] = [
    MockSource(),
    ...
    HackerNewsSource(),   # ← add here
]
```

Add the key to `SOURCES_ENABLED` in `.env.example` (and your `.env`) if it
should be on by default.

## 3. Test it

```python
# backend/tests/test_sources.py
def test_hackernews_available():
    assert HackerNewsSource().available() is True
```

Run `pytest tests -q`. Then create a campaign in the UI, tick your new source
(it appears automatically), hit **Run now** and check the per-source stats on
the campaign page.
