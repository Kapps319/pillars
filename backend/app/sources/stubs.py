"""Adapter stubs for platforms whose APIs do NOT allow public keyword search.

Why these are stubs and not implementations:
- Instagram / Facebook: the Meta Graph API only reaches pages/accounts you own
  or manage. There is no sanctioned endpoint for public keyword/lead search,
  and scraping the apps violates Meta's ToS.
- LinkedIn: the official API has no public post-search product at all;
  scraping LinkedIn violates its User Agreement (and has been litigated).

The architecture is ready — if these platforms ever ship a compliant search
API, implement search() here and flip enabled_by_default. We ship nothing that
violates ToS.
"""

from __future__ import annotations

from app.sources.base import RawPost, SearchFilters, SourceAdapter


class _UnsupportedPlatformSource(SourceAdapter):
    enabled_by_default = False
    reason = "This platform's official API does not permit public keyword/lead search."

    def available(self) -> bool:
        return False

    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        raise NotImplementedError(f"{self.name}: {self.reason}")


class InstagramSource(_UnsupportedPlatformSource):
    key = "instagram"
    name = "Instagram"
    description = "Not available: Graph API only reaches accounts you own; no public keyword search."


class FacebookSource(_UnsupportedPlatformSource):
    key = "facebook"
    name = "Facebook"
    description = "Not available: Graph API only reaches pages you manage; no public keyword search."


class LinkedInSource(_UnsupportedPlatformSource):
    key = "linkedin"
    name = "LinkedIn"
    description = "Not available: LinkedIn has no public post-search API; scraping violates its User Agreement."
