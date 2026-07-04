"""SourceAdapter — the single interface every data source implements.

Design rules:
- Public data + official APIs only. No login-walled scraping, no ToS violations.
- An adapter whose keys are missing reports available() == False and is skipped
  (logged, never crashes the job).
- search() may raise SourceError for transient failures; the job runner logs
  and continues with other sources.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    location: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = 25
    # For the manual_url source: explicit URLs to ingest
    urls: list[str] = Field(default_factory=list)


class RawPost(BaseModel):
    """Normalized post shape every adapter returns."""

    source_key: str
    external_id: str
    content: str
    title: str | None = None
    author: str | None = None
    url: str | None = None
    posted_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class SourceError(Exception):
    """Transient/source-level failure; the job logs it and skips the source."""


class SourceAdapter(ABC):
    key: str = "abstract"
    name: str = "Abstract source"
    description: str = ""
    # Env var names this adapter needs (shown in the UI / sources API)
    required_keys: list[str] = []
    # Adapters that are architecture-ready but must not run by default
    enabled_by_default: bool = True

    @abstractmethod
    def search(self, query: str, filters: SearchFilters) -> list[RawPost]:
        """Return normalized public posts matching the query."""

    def available(self) -> bool:
        """True when all required credentials/config are present."""
        return True

    def missing_keys(self) -> list[str]:
        return [] if self.available() else list(self.required_keys)
