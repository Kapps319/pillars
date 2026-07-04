"""Reddit source — official API via an OAuth "script" app (free tier).

Setup (see README):
  1. Create an app at https://www.reddit.com/prefs/apps (type: script)
  2. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

Uses the client_credentials grant, then GET /search on oauth.reddit.com.
Respects Reddit's rate limits by keeping requests minimal (one search call per
job per campaign).
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.sources.base import RawPost, SearchFilters, SourceAdapter, SourceError

logger = get_logger(__name__)

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_SEARCH_URL = "https://oauth.reddit.com/search"


class RedditSource(SourceAdapter):
    key = "reddit"
    name = "Reddit"
    description = "Official Reddit search API (OAuth script app, free tier)."
    # API keys required: create a 'script' app at reddit.com/prefs/apps
    required_keys = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]

    def __init__(self, client_id: str | None = None, client_secret: str | None = None, user_agent: str | None = None):
        settings = get_settings()
        self._client_id = client_id or settings.reddit_client_id
        self._client_secret = client_secret or settings.reddit_client_secret
        self._user_agent = user_agent or settings.reddit_user_agent

    def available(self) -> bool:
        return bool(self._client_id and self._client_secret and self._user_agent)

    def _get_token(self) -> str:
        response = httpx.post(
            _TOKEN_URL,
            auth=(self._client_id, self._client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self._user_agent},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        if not self.available():
            raise SourceError("Reddit credentials missing (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET)")
        try:
            token = self._get_token()
            response = httpx.get(
                _SEARCH_URL,
                params={"q": query, "limit": min(filters.limit, 100), "sort": "new", "type": "link"},
                headers={"Authorization": f"Bearer {token}", "User-Agent": self._user_agent},
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceError(f"Reddit API error: {exc}") from exc

        posts: list[RawPost] = []
        for child in response.json().get("data", {}).get("children", []):
            data = child.get("data", {})
            content = data.get("selftext") or data.get("title") or ""
            if not content.strip():
                continue
            posts.append(
                RawPost(
                    source_key=self.key,
                    external_id=data.get("name", data.get("id", "")),
                    content=content[:8000],
                    title=data.get("title"),
                    author=data.get("author"),
                    url=f"https://www.reddit.com{data['permalink']}" if data.get("permalink") else data.get("url"),
                    posted_at=datetime.fromtimestamp(data["created_utc"], tz=timezone.utc)
                    if data.get("created_utc")
                    else None,
                    metadata={"subreddit": data.get("subreddit"), "score": data.get("score")},
                )
            )
        logger.info("Reddit search returned %d posts for query '%s'", len(posts), query)
        return posts
