"""Manual URL ingestion — a robots.txt-aware, rate-limited public-page scraper.

The user submits public URLs (via SearchFilters.urls); each page is fetched,
its main text extracted with BeautifulSoup, and returned as one RawPost.
Pages disallowed by robots.txt are skipped and logged — never bypassed.
"""

from __future__ import annotations

import hashlib
import threading
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.logging import get_logger
from app.sources.base import RawPost, SearchFilters, SourceAdapter

logger = get_logger(__name__)


class _HostRateLimiter:
    """Minimum delay between requests to the same host (per process)."""

    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last.get(host, 0.0)
            sleep_for = max(0.0, self._min_interval - elapsed)
            self._last[host] = now + sleep_for
        if sleep_for > 0:
            time.sleep(sleep_for)


class ManualUrlSource(SourceAdapter):
    key = "manual_url"
    name = "Manual URL ingestion"
    description = "Paste any public URL; a robots.txt-aware scraper turns the page into a post."
    required_keys: list[str] = []

    def __init__(self):
        settings = get_settings()
        self._user_agent = settings.scraper_user_agent
        self._timeout = settings.scraper_timeout_seconds
        self._limiter = _HostRateLimiter(settings.scraper_rate_limit_seconds)
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _robots_allows(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._robots_cache.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
            except Exception:
                # Unreachable robots.txt -> assume allowed (standard convention)
                rp.allow_all = True
            self._robots_cache[base] = rp
        return rp.can_fetch(self._user_agent, url)

    def _fetch_page(self, url: str) -> RawPost | None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning("manual_url: skipping non-http URL %s", url)
            return None
        if not self._robots_allows(url):
            logger.warning("manual_url: robots.txt disallows %s — skipping", url)
            return None

        self._limiter.wait(parsed.netloc)
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": self._user_agent},
                timeout=self._timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("manual_url: fetch failed for %s: %s", url, exc)
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        title = soup.title.get_text(strip=True) if soup.title else None
        text = " ".join(soup.get_text(separator=" ").split())
        if not text:
            return None
        return RawPost(
            source_key=self.key,
            external_id=hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
            content=text[:8000],
            title=title,
            author=parsed.netloc,
            url=url,
            posted_at=None,
            metadata={"fetched_from": parsed.netloc},
        )

    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        # This adapter ingests explicit URLs rather than searching. Called with
        # no URLs (e.g. during a normal campaign run) it simply contributes 0 posts.
        posts: list[RawPost] = []
        for url in filters.urls[: filters.limit]:
            post = self._fetch_page(url)
            if post:
                posts.append(post)
        return posts
