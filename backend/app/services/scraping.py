"""Scraping job runner.

The same function runs inside a Celery worker or synchronously in-process
(the fallback that lets `docker compose up` work without a worker, and the
demo run keyless). Every source failure is logged into job.stats and skipped —
one broken source never fails the job.
"""

from __future__ import annotations

import threading

from sqlalchemy.orm import Session

from app.classifier.llm import get_llm_client
from app.classifier.pipeline import classify_post
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.base import utcnow
from app.db.session import get_sessionmaker
from app.models import Campaign, IntentLabel, IntentTarget, JobStatus, Lead, LeadClassification, ScrapingJob
from app.sources import SearchFilters, get_registry
from app.sources.base import SourceError

logger = get_logger(__name__)


def ingest_post(db: Session, campaign: Campaign, post, llm_client) -> Lead | None:
    """Classify one RawPost and persist it as a Lead (or return None if filtered/duplicate)."""
    existing = (
        db.query(Lead)
        .filter(
            Lead.campaign_id == campaign.id,
            Lead.source_key == post.source_key,
            Lead.external_id == post.external_id,
        )
        .first()
    )
    if existing:
        return None

    text = f"{post.title}. {post.content}" if post.title and post.title not in post.content else post.content
    result = classify_post(
        text=text,
        campaign_product=campaign.product_keyword,
        campaign_location=campaign.location,
        posted_at=post.posted_at,
        llm_client=llm_client,
    )

    if result.confidence < campaign.min_confidence:
        return None
    # Campaign intent target filter: a Buyers campaign doesn't collect SELL posts
    if campaign.intent_target == IntentTarget.BUYERS and result.intent == IntentLabel.SELL:
        return None
    if campaign.intent_target == IntentTarget.SELLERS and result.intent == IntentLabel.BUY:
        return None

    lead = Lead(
        campaign_id=campaign.id,
        source_key=post.source_key,
        external_id=post.external_id,
        url=post.url,
        author=post.author,
        title=post.title,
        content=post.content,
        posted_at=post.posted_at,
        product=result.extracted.get("product"),
        price_value=result.extracted.get("price"),
        price_currency=result.extracted.get("currency"),
        location=result.extracted.get("location"),
        event_date=result.extracted.get("date"),
        score=result.score,
        raw=post.metadata,
    )
    lead.classification = LeadClassification(
        intent=result.intent,
        confidence=result.confidence,
        reasons=result.reasons,
        extracted=result.extracted,
        model=result.model,
        rule_signals=result.rule_signals,
    )
    db.add(lead)
    return lead


def execute_job(db: Session, job_id: int, urls: list[str] | None = None) -> None:
    job = db.get(ScrapingJob, job_id)
    if job is None:
        logger.error("ScrapingJob %s not found", job_id)
        return
    campaign = db.get(Campaign, job.campaign_id)
    if campaign is None:
        job.status = JobStatus.FAILED
        job.error = "Campaign not found"
        db.commit()
        return

    job.status = JobStatus.RUNNING
    job.started_at = utcnow()
    db.commit()

    llm_client = get_llm_client()
    registry = get_registry()
    filters = SearchFilters(
        location=campaign.location,
        date_from=campaign.date_from,
        date_to=campaign.date_to,
        urls=urls or [],
    )
    stats: dict = {}

    try:
        adapters = registry.runnable(campaign.sources or None)
        # Report every selected-but-skipped source so the UI can explain why
        for key in campaign.sources or []:
            if key not in [a.key for a in adapters]:
                adapter = registry.get(key)
                reason = "unknown source" if adapter is None else (
                    f"missing keys: {', '.join(adapter.missing_keys())}" if not (adapter.available()) else "disabled"
                )
                stats[key] = {"skipped": reason}

        for adapter in adapters:
            try:
                posts = adapter.search(campaign.product_keyword, filters)
            except (SourceError, NotImplementedError) as exc:
                logger.warning("Source '%s' failed: %s — skipping", adapter.key, exc)
                stats[adapter.key] = {"error": str(exc)}
                continue
            created = 0
            for post in posts:
                if ingest_post(db, campaign, post, llm_client):
                    created += 1
            db.commit()
            stats[adapter.key] = {"fetched": len(posts), "created": created}

        job.status = JobStatus.SUCCESS
    except Exception as exc:  # never leave a job stuck in RUNNING
        logger.exception("Job %s failed", job_id)
        db.rollback()
        job = db.get(ScrapingJob, job_id)
        job.status = JobStatus.FAILED
        job.error = str(exc)[:2000]
    finally:
        job.stats = stats
        job.finished_at = utcnow()
        db.commit()


def run_job_standalone(job_id: int, urls: list[str] | None = None) -> None:
    """Entry point used by both the Celery task and the sync fallback thread."""
    db = get_sessionmaker()()
    try:
        execute_job(db, job_id, urls)
    finally:
        db.close()


def enqueue_job(job_id: int, urls: list[str] | None = None) -> str:
    """Queue the job on Celery; if the broker is unreachable or Celery is
    disabled, run it in a background thread instead (synchronous fallback).
    Returns the execution mode for observability.
    """
    settings = get_settings()
    if settings.celery_enabled:
        try:
            from app.workers.tasks import run_scraping_job_task

            run_scraping_job_task.apply_async(args=[job_id, urls], retry=False)
            return "celery"
        except Exception as exc:
            logger.warning("Celery enqueue failed (%s) — running job %s in-process", exc, job_id)

    thread = threading.Thread(target=run_job_standalone, args=(job_id, urls), daemon=True)
    thread.start()
    return "inline"
