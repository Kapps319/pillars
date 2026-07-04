from __future__ import annotations

from pydantic import BaseModel


class SourceOut(BaseModel):
    key: str
    name: str
    description: str
    enabled: bool
    available: bool
    missing_keys: list[str]
    required_keys: list[str]
    implemented: bool


class ManualIngestRequest(BaseModel):
    campaign_id: int
    urls: list[str]
