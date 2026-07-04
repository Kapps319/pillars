from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DbDep, UserDep
from app.models import AuditLog, Campaign, JobStatus, Lead, ScrapingJob
from app.schemas.campaign import (
    CampaignCreate,
    CampaignOut,
    CampaignUpdate,
    CampaignWithStats,
    JobOut,
    RunCampaignRequest,
    RunCampaignResponse,
)
from app.services.scraping import enqueue_job

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _get_owned_campaign(db, user_id: int, campaign_id: int) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or campaign.is_deleted or campaign.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return campaign


@router.get("", response_model=list[CampaignWithStats])
def list_campaigns(db: DbDep, user: UserDep) -> list[CampaignWithStats]:
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.user_id == user.id, Campaign.is_deleted.is_(False))
        .order_by(Campaign.created_at.desc())
        .all()
    )
    lead_counts = dict(
        db.execute(
            select(Lead.campaign_id, func.count(Lead.id))
            .where(Lead.campaign_id.in_([c.id for c in campaigns]) if campaigns else False, Lead.is_deleted.is_(False))
            .group_by(Lead.campaign_id)
        ).all()
    )
    out: list[CampaignWithStats] = []
    for c in campaigns:
        last_job = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.campaign_id == c.id)
            .order_by(ScrapingJob.created_at.desc())
            .first()
        )
        item = CampaignWithStats.model_validate(c)
        item.lead_count = lead_counts.get(c.id, 0)
        item.last_job_status = last_job.status if last_job else None
        item.last_job_at = last_job.created_at if last_job else None
        out.append(item)
    return out


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, db: DbDep, user: UserDep) -> Campaign:
    campaign = Campaign(user_id=user.id, **payload.model_dump())
    db.add(campaign)
    db.add(AuditLog(user_id=user.id, action="campaign.create", entity_type="campaign", meta={"name": payload.name}))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignWithStats)
def get_campaign(campaign_id: int, db: DbDep, user: UserDep) -> CampaignWithStats:
    campaign = _get_owned_campaign(db, user.id, campaign_id)
    item = CampaignWithStats.model_validate(campaign)
    item.lead_count = (
        db.query(func.count(Lead.id)).filter(Lead.campaign_id == campaign.id, Lead.is_deleted.is_(False)).scalar() or 0
    )
    last_job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.campaign_id == campaign.id)
        .order_by(ScrapingJob.created_at.desc())
        .first()
    )
    item.last_job_status = last_job.status if last_job else None
    item.last_job_at = last_job.created_at if last_job else None
    return item


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, payload: CampaignUpdate, db: DbDep, user: UserDep) -> Campaign:
    campaign = _get_owned_campaign(db, user.id, campaign_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, key, value)
    db.add(AuditLog(user_id=user.id, action="campaign.update", entity_type="campaign", entity_id=str(campaign_id)))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: int, db: DbDep, user: UserDep) -> None:
    campaign = _get_owned_campaign(db, user.id, campaign_id)
    campaign.is_deleted = True  # soft delete
    db.add(AuditLog(user_id=user.id, action="campaign.delete", entity_type="campaign", entity_id=str(campaign_id)))
    db.commit()


@router.post("/{campaign_id}/run", response_model=RunCampaignResponse, status_code=status.HTTP_202_ACCEPTED)
def run_campaign(campaign_id: int, payload: RunCampaignRequest, db: DbDep, user: UserDep) -> RunCampaignResponse:
    campaign = _get_owned_campaign(db, user.id, campaign_id)
    job = ScrapingJob(campaign_id=campaign.id, status=JobStatus.PENDING)
    db.add(job)
    db.add(AuditLog(user_id=user.id, action="campaign.run", entity_type="campaign", entity_id=str(campaign_id)))
    db.commit()
    db.refresh(job)
    execution = enqueue_job(job.id, payload.urls or None)
    return RunCampaignResponse(job=JobOut.model_validate(job), execution=execution)


@router.get("/{campaign_id}/jobs", response_model=list[JobOut])
def list_jobs(campaign_id: int, db: DbDep, user: UserDep) -> list[ScrapingJob]:
    _get_owned_campaign(db, user.id, campaign_id)
    return (
        db.query(ScrapingJob)
        .filter(ScrapingJob.campaign_id == campaign_id)
        .order_by(ScrapingJob.created_at.desc())
        .limit(20)
        .all()
    )
