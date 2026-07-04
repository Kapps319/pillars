from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbDep, UserDep
from app.models import Campaign, JobStatus, ScrapingJob
from app.schemas.campaign import JobOut, RunCampaignResponse
from app.schemas.source import ManualIngestRequest, SourceOut
from app.services.scraping import enqueue_job
from app.sources import get_registry
from app.sources.stubs import _UnsupportedPlatformSource

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(user: UserDep) -> list[SourceOut]:
    registry = get_registry()
    out: list[SourceOut] = []
    for adapter in registry.all():
        implemented = not isinstance(adapter, _UnsupportedPlatformSource)
        out.append(
            SourceOut(
                key=adapter.key,
                name=adapter.name,
                description=adapter.description,
                enabled=registry.is_enabled(adapter.key),
                available=adapter.available(),
                missing_keys=adapter.missing_keys(),
                required_keys=adapter.required_keys,
                implemented=implemented,
            )
        )
    return out


@router.post("/ingest-url", response_model=RunCampaignResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_urls(payload: ManualIngestRequest, db: DbDep, user: UserDep) -> RunCampaignResponse:
    """Manual URL ingestion: parse submitted public URLs into leads for a campaign."""
    campaign = db.get(Campaign, payload.campaign_id)
    if campaign is None or campaign.is_deleted or campaign.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    if not payload.urls:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No URLs provided")
    job = ScrapingJob(campaign_id=campaign.id, status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)
    execution = enqueue_job(job.id, payload.urls)
    return RunCampaignResponse(job=JobOut.model_validate(job), execution=execution)
