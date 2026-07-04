"""Source registry — sources are enabled/disabled via config (SOURCES_ENABLED)
plus per-source DB toggles managed through the Sources API.

Adding a new source is drop-in: implement SourceAdapter, add it to _ADAPTERS.
See docs/ADDING_A_SOURCE.md.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger
from app.sources.base import SourceAdapter
from app.sources.google_source import GoogleSource
from app.sources.manual_url import ManualUrlSource
from app.sources.mock_source import MockSource
from app.sources.reddit_source import RedditSource
from app.sources.stubs import FacebookSource, InstagramSource, LinkedInSource
from app.sources.twitter_source import TwitterSource

logger = get_logger(__name__)


class SourceRegistry:
    def __init__(self, adapters: list[SourceAdapter], enabled_keys: list[str]):
        self._adapters: dict[str, SourceAdapter] = {a.key: a for a in adapters}
        self._enabled = set(enabled_keys)

    def all(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def get(self, key: str) -> SourceAdapter | None:
        return self._adapters.get(key)

    def is_enabled(self, key: str) -> bool:
        adapter = self._adapters.get(key)
        if adapter is None:
            return False
        if not adapter.enabled_by_default and key not in self._enabled:
            return False
        return key in self._enabled

    def runnable(self, keys: list[str] | None = None) -> list[SourceAdapter]:
        """Adapters that are enabled AND have their credentials — the set a job runs.

        `keys` optionally restricts to a campaign's selected sources.
        """
        selected = keys if keys else list(self._enabled)
        out: list[SourceAdapter] = []
        for key in selected:
            adapter = self._adapters.get(key)
            if adapter is None:
                logger.warning("Unknown source key '%s' — skipping", key)
                continue
            if not self.is_enabled(key):
                logger.info("Source '%s' is disabled — skipping", key)
                continue
            if not adapter.available():
                logger.warning("Source '%s' missing keys %s — skipping", key, adapter.missing_keys())
                continue
            out.append(adapter)
        return out


@lru_cache
def get_registry() -> SourceRegistry:
    settings = get_settings()
    adapters: list[SourceAdapter] = [
        MockSource(),
        RedditSource(),
        GoogleSource(),
        ManualUrlSource(),
        TwitterSource(),
        InstagramSource(),
        FacebookSource(),
        LinkedInSource(),
    ]
    return SourceRegistry(adapters, settings.enabled_source_keys)
