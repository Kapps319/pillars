from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import IntentLabel, LeadStatus


class ClassificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intent: IntentLabel
    confidence: int
    reasons: list[str]
    extracted: dict
    model: str
    rule_signals: dict


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    source_key: str
    external_id: str
    url: str | None
    author: str | None
    title: str | None
    content: str
    posted_at: datetime | None
    product: str | None
    price_value: float | None
    price_currency: str | None
    location: str | None
    event_date: str | None
    status: LeadStatus
    score: int
    created_at: datetime
    classification: ClassificationOut | None


class LeadStatusUpdate(BaseModel):
    status: LeadStatus


class DashboardStats(BaseModel):
    total_leads: int
    by_intent: dict[str, int]
    by_status: dict[str, int]
    by_source: dict[str, int]
    campaigns: int
    avg_score: float
    recent_leads: list[LeadOut]
    leads_last_14_days: list[dict]  # [{"date": "2026-07-01", "count": 3}]
