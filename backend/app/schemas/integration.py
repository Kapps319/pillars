from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    key_name: str = Field(min_length=1, max_length=128, pattern=r"^[A-Z0-9_]+$")
    value: str = Field(min_length=1, max_length=4096)


class IntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    key_name: str
    masked_value: str
    created_at: datetime
    updated_at: datetime


class AdminSettingsOut(BaseModel):
    llm_provider: str
    llm_available: bool
    llm_model: str
    search_backend: str
    celery_enabled: bool
    sources_enabled: list[str]
    environment: str
