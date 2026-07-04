from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbDep, UserDep
from app.models import Campaign, ScrapingJob
from app.schemas.campaign import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: DbDep, user: UserDep) -> ScrapingJob:
    job = db.get(ScrapingJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    campaign = db.get(Campaign, job.campaign_id)
    if campaign is None or campaign.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job
