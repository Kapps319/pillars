from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.deps import DbDep, UserDep
from app.models import AuditLog, Campaign, IntentLabel, Lead, LeadClassification, LeadStatus
from app.schemas.common import Page
from app.schemas.lead import DashboardStats, LeadOut, LeadStatusUpdate
from app.services.leads import build_leads_query, leads_to_csv

router = APIRouter(prefix="/leads", tags=["leads"])


def _query_leads(
    db,
    user_id: int,
    campaign_id: int | None,
    intent: IntentLabel | None,
    lead_status: LeadStatus | None,
    min_score: int | None,
    source: str | None,
    location: str | None,
    product: str | None,
    q: str | None,
    date_from: date | None,
    date_to: date | None,
    sort_by: str,
    sort_dir: str,
):
    return build_leads_query(
        db,
        user_id,
        campaign_id=campaign_id,
        intent=intent,
        status=lead_status,
        min_score=min_score,
        source_key=source,
        location=location,
        product=product,
        q=q,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("", response_model=Page[LeadOut])
def list_leads(
    db: DbDep,
    user: UserDep,
    campaign_id: int | None = None,
    intent: IntentLabel | None = None,
    lead_status: LeadStatus | None = Query(default=None, alias="status"),
    min_score: int | None = Query(default=None, ge=0, le=100),
    source: str | None = None,
    location: str | None = None,
    product: str | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: Literal["score", "posted_at", "created_at", "status"] = "score",
    sort_dir: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> Page[LeadOut]:
    stmt = _query_leads(
        db, user.id, campaign_id, intent, lead_status, min_score, source, location, product, q,
        date_from, date_to, sort_by, sort_dir,
    )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).unique().scalars().all()
    return Page(items=[LeadOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/export.csv")
def export_csv(
    db: DbDep,
    user: UserDep,
    campaign_id: int | None = None,
    intent: IntentLabel | None = None,
    lead_status: LeadStatus | None = Query(default=None, alias="status"),
    min_score: int | None = Query(default=None, ge=0, le=100),
    source: str | None = None,
    location: str | None = None,
    product: str | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: Literal["score", "posted_at", "created_at", "status"] = "score",
    sort_dir: Literal["asc", "desc"] = "desc",
) -> StreamingResponse:
    stmt = _query_leads(
        db, user.id, campaign_id, intent, lead_status, min_score, source, location, product, q,
        date_from, date_to, sort_by, sort_dir,
    )
    leads = db.execute(stmt.limit(10_000)).unique().scalars().all()
    filename = f"leads-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        leads_to_csv(leads),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(db: DbDep, user: UserDep) -> DashboardStats:
    base = (
        select(Lead)
        .join(Campaign, Lead.campaign_id == Campaign.id)
        .where(Campaign.user_id == user.id, Lead.is_deleted.is_(False))
    )
    lead_ids = select(base.subquery().c.id)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    by_intent = dict(
        db.execute(
            select(LeadClassification.intent, func.count())
            .where(LeadClassification.lead_id.in_(lead_ids))
            .group_by(LeadClassification.intent)
        ).all()
    )
    lead_subq = base.subquery()
    by_status = dict(db.execute(select(lead_subq.c.status, func.count()).group_by(lead_subq.c.status)).all())
    by_source = dict(db.execute(select(lead_subq.c.source_key, func.count()).group_by(lead_subq.c.source_key)).all())
    avg_score = db.scalar(select(func.avg(lead_subq.c.score))) or 0.0
    campaigns = (
        db.scalar(
            select(func.count()).select_from(Campaign).where(Campaign.user_id == user.id, Campaign.is_deleted.is_(False))
        )
        or 0
    )

    recent = db.execute(build_leads_query(db, user.id, sort_by="created_at").limit(5)).unique().scalars().all()

    # Simple leads-per-day series for the dashboard chart
    since = datetime.now(timezone.utc) - timedelta(days=14)
    day_rows = db.execute(
        select(func.date(lead_subq.c.created_at), func.count())
        .where(lead_subq.c.created_at >= since)
        .group_by(func.date(lead_subq.c.created_at))
        .order_by(func.date(lead_subq.c.created_at))
    ).all()
    series = [{"date": str(d), "count": c} for d, c in day_rows]

    return DashboardStats(
        total_leads=total,
        by_intent={k.value if hasattr(k, "value") else str(k): v for k, v in by_intent.items()},
        by_status={k.value if hasattr(k, "value") else str(k): v for k, v in by_status.items()},
        by_source={str(k): v for k, v in by_source.items()},
        campaigns=campaigns,
        avg_score=round(float(avg_score), 1),
        recent_leads=[LeadOut.model_validate(r) for r in recent],
        leads_last_14_days=series,
    )


def _get_owned_lead(db, user_id: int, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    campaign = db.get(Campaign, lead.campaign_id)
    if campaign is None or campaign.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    return lead


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: DbDep, user: UserDep) -> Lead:
    return _get_owned_lead(db, user.id, lead_id)


@router.patch("/{lead_id}/status", response_model=LeadOut)
def update_lead_status(lead_id: int, payload: LeadStatusUpdate, db: DbDep, user: UserDep) -> Lead:
    lead = _get_owned_lead(db, user.id, lead_id)
    lead.status = payload.status
    db.add(
        AuditLog(
            user_id=user.id,
            action="lead.status_change",
            entity_type="lead",
            entity_id=str(lead_id),
            meta={"status": payload.status.value},
        )
    )
    db.commit()
    db.refresh(lead)
    return lead
