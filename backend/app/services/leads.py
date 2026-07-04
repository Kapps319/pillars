"""Lead querying: filters, full-text search, sorting, pagination, CSV export."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from datetime import date, datetime, time, timezone

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Campaign, IntentLabel, Lead, LeadClassification, LeadStatus

logger = get_logger(__name__)

SORTABLE = {
    "score": Lead.score,
    "posted_at": Lead.posted_at,
    "created_at": Lead.created_at,
    "status": Lead.status,
}


def _apply_text_search(stmt: Select, q: str, db: Session) -> Select:
    """Postgres full-text search for MVP; ILIKE fallback elsewhere (tests/SQLite).

    SEARCH_BACKEND=elasticsearch is accepted but not implemented — it logs a
    warning and uses the Postgres path so nothing breaks.
    """
    settings = get_settings()
    if settings.search_backend == "elasticsearch":
        logger.warning("SEARCH_BACKEND=elasticsearch is not implemented yet — falling back to postgres")
    if db.get_bind().dialect.name == "postgresql":
        tsquery = func.plainto_tsquery("english", q)
        return stmt.where(
            func.to_tsvector("english", func.coalesce(Lead.title, "") + " " + Lead.content).op("@@")(tsquery)
        )
    pattern = f"%{q}%"
    return stmt.where(or_(Lead.content.ilike(pattern), Lead.title.ilike(pattern)))


def build_leads_query(
    db: Session,
    user_id: int,
    campaign_id: int | None = None,
    intent: IntentLabel | None = None,
    status: LeadStatus | None = None,
    min_score: int | None = None,
    source_key: str | None = None,
    location: str | None = None,
    product: str | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = "score",
    sort_dir: str = "desc",
) -> Select:
    stmt = (
        select(Lead)
        .join(Campaign, Lead.campaign_id == Campaign.id)
        .join(LeadClassification, LeadClassification.lead_id == Lead.id, isouter=True)
        .options(joinedload(Lead.classification), joinedload(Lead.campaign))
        .where(Campaign.user_id == user_id, Lead.is_deleted.is_(False))
    )
    if campaign_id is not None:
        stmt = stmt.where(Lead.campaign_id == campaign_id)
    if intent is not None:
        stmt = stmt.where(LeadClassification.intent == intent)
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    if min_score is not None:
        stmt = stmt.where(Lead.score >= min_score)
    if source_key:
        stmt = stmt.where(Lead.source_key == source_key)
    if location:
        stmt = stmt.where(Lead.location.ilike(f"%{location}%"))
    if product:
        stmt = stmt.where(or_(Lead.product.ilike(f"%{product}%"), Lead.content.ilike(f"%{product}%")))
    if q:
        stmt = _apply_text_search(stmt, q, db)
    if date_from:
        stmt = stmt.where(Lead.posted_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        stmt = stmt.where(Lead.posted_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))

    column = SORTABLE.get(sort_by, Lead.score)
    stmt = stmt.order_by(column.desc() if sort_dir == "desc" else column.asc(), Lead.id.desc())
    return stmt


CSV_COLUMNS = [
    "id", "campaign", "source", "intent", "confidence", "score", "status",
    "author", "title", "content", "product", "price", "currency", "location",
    "event_date", "url", "posted_at", "reasons",
]


def leads_to_csv(leads: list[Lead]) -> Iterator[str]:
    """Stream leads as CSV rows."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    yield buffer.getvalue()
    for lead in leads:
        buffer.seek(0)
        buffer.truncate(0)
        c = lead.classification
        writer.writerow([
            lead.id,
            lead.campaign.name if lead.campaign else "",
            lead.source_key,
            c.intent.value if c else "",
            c.confidence if c else "",
            lead.score,
            lead.status.value,
            lead.author or "",
            lead.title or "",
            lead.content.replace("\n", " ")[:1000],
            lead.product or "",
            lead.price_value if lead.price_value is not None else "",
            lead.price_currency or "",
            lead.location or "",
            lead.event_date or "",
            lead.url or "",
            lead.posted_at.isoformat() if lead.posted_at else "",
            "; ".join(c.reasons) if c else "",
        ])
        yield buffer.getvalue()
