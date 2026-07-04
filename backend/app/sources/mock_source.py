"""Mock/sample source — reads local JSON fixtures of realistic posts.

Default ON and needs no keys: this is what makes the dashboard populated on
first boot. Filtering is a lightweight keyword match so campaigns for
different products get different subsets.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from app.core.config import FIXTURES_DIR
from app.sources.base import RawPost, SearchFilters, SourceAdapter

_STOPWORDS = {"the", "a", "an", "of", "for", "in", "to", "and", "or", "ticket", "tickets"}


@lru_cache
def _load_fixtures(path_str: str) -> list[dict]:
    with open(path_str, encoding="utf-8") as fh:
        return json.load(fh)


class MockSource(SourceAdapter):
    key = "mock"
    name = "Sample data (offline)"
    description = "Local JSON fixtures of ~30 realistic posts. No keys needed; ideal for demos and tests."
    required_keys: list[str] = []

    def __init__(self, fixtures_path: Path | None = None):
        self._path = str(fixtures_path or FIXTURES_DIR / "sample_posts.json")

    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        posts = _load_fixtures(self._path)
        tokens = [t for t in re.split(r"\W+", query.lower()) if t and t not in _STOPWORDS]

        results: list[RawPost] = []
        for post in posts:
            haystack = f"{post.get('title', '')} {post.get('content', '')} {' '.join(post.get('tags', []))}".lower()
            # Match any meaningful token; an empty query returns everything
            if tokens and not any(t in haystack for t in tokens):
                continue
            results.append(
                RawPost(
                    source_key=self.key,
                    external_id=post["external_id"],
                    content=post["content"],
                    title=post.get("title"),
                    author=post.get("author"),
                    url=post.get("url"),
                    posted_at=datetime.fromisoformat(post["posted_at"].replace("Z", "+00:00"))
                    if post.get("posted_at")
                    else None,
                    metadata={"tags": post.get("tags", [])},
                )
            )
            if len(results) >= filters.limit:
                break
        return results
