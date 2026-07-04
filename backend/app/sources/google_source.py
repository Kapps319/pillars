"""Google web search source — Custom Search JSON API (100 free queries/day).

Setup (see README):
  1. Create an API key at https://console.cloud.google.com (Custom Search API)
  2. Create a Programmable Search Engine at https://programmablesearchengine.google.com
  3. Set GOOGLE_API_KEY and GOOGLE_CSE_ID
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.sources.base import RawPost, SearchFilters, SourceAdapter, SourceError

logger = get_logger(__name__)

_API_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSource(SourceAdapter):
    key = "google"
    name = "Google web search"
    description = "Google Custom Search JSON API (100 free queries/day)."
    # API keys required: Google Cloud API key + Programmable Search Engine ID
    required_keys = ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"]

    def __init__(self, api_key: str | None = None, cse_id: str | None = None):
        settings = get_settings()
        self._api_key = api_key or settings.google_api_key
        self._cse_id = cse_id or settings.google_cse_id

    def available(self) -> bool:
        return bool(self._api_key and self._cse_id)

    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        if not self.available():
            raise SourceError("Google CSE credentials missing (GOOGLE_API_KEY / GOOGLE_CSE_ID)")
        try:
            response = httpx.get(
                _API_URL,
                params={
                    "key": self._api_key,
                    "cx": self._cse_id,
                    "q": query,
                    "num": min(filters.limit, 10),  # CSE caps at 10 per request
                },
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceError(f"Google CSE error: {exc}") from exc

        posts: list[RawPost] = []
        for item in response.json().get("items", []):
            link = item.get("link", "")
            snippet = item.get("snippet") or ""
            title = item.get("title") or ""
            if not (snippet or title):
                continue
            posts.append(
                RawPost(
                    source_key=self.key,
                    # CSE results have no stable id — hash the URL
                    external_id=hashlib.sha1(link.encode("utf-8")).hexdigest()[:16],
                    content=f"{title}. {snippet}"[:8000],
                    title=title,
                    author=item.get("displayLink"),
                    url=link,
                    posted_at=None,  # CSE doesn't expose publish dates reliably
                    metadata={"display_link": item.get("displayLink")},
                )
            )
        logger.info("Google CSE returned %d results for query '%s'", len(posts), query)
        return posts
