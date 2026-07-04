from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IntentTarget, JobStatus


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    product_keyword: str = Field(min_length=1, max_length=255)
    intent_target: IntentTarget = IntentTarget.BOTH
    location: str | None = Field(default=None, max_length=255)
    date_from: date | None = None
    date_to: date | None = None
    min_confidence: int = Field(default=0, ge=0, le=100)
    sources: list[str] = Field(default_factory=lambda: ["mock"])


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    product_keyword: str | None = Field(default=None, min_length=1, max_length=255)
    intent_target: IntentTarget | None = None
    location: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_confidence: int | None = Field(default=None, ge=0, le=100)
    sources: list[str] | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    product_keyword: str
    intent_target: IntentTarget
    location: str | None
    date_from: date | None
    date_to: date | None
    min_confidence: int
    sources: list[str]
    created_at: datetime
    updated_at: datetime


class CampaignWithStats(CampaignOut):
    lead_count: int = 0
    last_job_status: JobStatus | None = None
    last_job_at: datetime | None = None


class RunCampaignRequest(BaseModel):
    # Optional explicit URLs for the manual_url source
    urls: list[str] = Field(default_factory=list, max_length=20)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    status: JobStatus
    started_at: datetime | None
    finished_at: datetime | None
    stats: dict
    error: str | None
    created_at: datetime


class RunCampaignResponse(BaseModel):
    job: JobOut
    execution: str  # "celery" | "inline"
