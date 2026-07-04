"""X/Twitter source — built and ready, but DISABLED by default.

The X API v2 recent-search endpoint requires a paid tier; running it by
accident would burn quota/money. Set TWITTER_BEARER and add "twitter" to
SOURCES_ENABLED to activate — no code changes needed.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.sources.base import RawPost, SearchFilters, SourceAdapter, SourceError

logger = get_logger(__name__)

_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class TwitterSource(SourceAdapter):
    key = "twitter"
    name = "X / Twitter"
    description = "X API v2 recent search. Paid API — disabled by default; set TWITTER_BEARER and enable explicitly."
    # API key required: X API v2 bearer token (paid tiers only)
    required_keys = ["TWITTER_BEARER"]
    enabled_by_default = False

    def __init__(self, bearer: str | None = None):
        self._bearer = bearer or get_settings().twitter_bearer

    def available(self) -> bool:
        return bool(self._bearer)

    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        if not self.available():
            raise SourceError("TWITTER_BEARER not configured")
        try:
            response = httpx.get(
                _SEARCH_URL,
                params={
                    "query": f"{query} -is:retweet lang:en",
                    "max_results": max(10, min(filters.limit, 100)),
                    "tweet.fields": "created_at,author_id,geo",
                },
                headers={"Authorization": f"Bearer {self._bearer}"},
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceError(f"X API error: {exc}") from exc

        posts: list[RawPost] = []
        for tweet in response.json().get("data", []):
            posts.append(
                RawPost(
                    source_key=self.key,
                    external_id=tweet["id"],
                    content=tweet.get("text", "")[:8000],
                    author=tweet.get("author_id"),
                    url=f"https://x.com/i/web/status/{tweet['id']}",
                    posted_at=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                    if tweet.get("created_at")
                    else None,
                )
            )
        return posts
