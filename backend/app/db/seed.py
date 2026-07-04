"""Idempotent demo seed: demo user, one campaign, sources, and leads generated
by running the full classification pipeline over the mock fixtures.

Run manually with `python -m app.db.seed` or automatically on startup when
SEED_ON_STARTUP=true (the docker compose default).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.classifier.llm.rules_client import RulesOnlyClient
from app.core.logging import get_logger, setup_logging
from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import Campaign, IntentTarget, JobStatus, ScrapingJob, SearchSource, User
from app.services.scraping import ingest_post
from app.sources import get_registry
from app.sources.base import SearchFilters
from app.sources.mock_source import MockSource

logger = get_logger(__name__)

DEMO_EMAIL = "demo@leadfinder.app"
DEMO_PASSWORD = "demo12345"  # documented in README; change for anything non-demo


def seed_sources(db: Session) -> None:
    registry = get_registry()
    for adapter in registry.all():
        if db.query(SearchSource).filter(SearchSource.key == adapter.key).first():
            continue
        db.add(
            SearchSource(
                key=adapter.key,
                name=adapter.name,
                description=adapter.description,
                enabled=registry.is_enabled(adapter.key),
                required_keys=adapter.required_keys,
            )
        )
    db.commit()


def seed_demo_user(db: Session) -> User:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Demo User",
            is_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Seeded demo user %s / %s", DEMO_EMAIL, DEMO_PASSWORD)
    return user


def seed_demo_campaign(db: Session, user: User) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.user_id == user.id, Campaign.name == "Ticket intent radar").first()
    if campaign is None:
        campaign = Campaign(
            user_id=user.id,
            name="Ticket intent radar",
            product_keyword="tickets",
            intent_target=IntentTarget.BOTH,
            location=None,
            min_confidence=0,
            sources=["mock"],
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
    return campaign


def seed_leads(db: Session, campaign: Campaign) -> int:
    """Ingest every fixture post through the real pipeline (rules-only client)."""
    mock = MockSource()
    posts = mock.search("", SearchFilters(limit=100))  # empty query = all fixtures
    llm = RulesOnlyClient()
    created = 0
    for post in posts:
        if ingest_post(db, campaign, post, llm):
            created += 1
    if created:
        job = ScrapingJob(campaign_id=campaign.id, status=JobStatus.SUCCESS,
                          stats={"mock": {"fetched": len(posts), "created": created}})
        db.add(job)
    db.commit()
    return created


def seed_all() -> None:
    db = get_sessionmaker()()
    try:
        seed_sources(db)
        user = seed_demo_user(db)
        campaign = seed_demo_campaign(db, user)
        created = seed_leads(db, campaign)
        logger.info("Seed complete: campaign '%s', %d new leads", campaign.name, created)
    finally:
        db.close()


if __name__ == "__main__":
    setup_logging()
    seed_all()
