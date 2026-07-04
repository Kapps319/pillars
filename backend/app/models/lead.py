from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import IntentLabel, LeadStatus

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class Lead(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "leads"
    __table_args__ = (
        # Dedupe: the same external post ingested twice for a campaign is one lead
        UniqueConstraint("campaign_id", "source_key", "external_id", name="uq_lead_campaign_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048))
    author: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    # Extracted fields (denormalized from the classification for easy filtering)
    product: Mapped[str | None] = mapped_column(String(255), index=True)
    price_value: Mapped[float | None] = mapped_column(Float)
    price_currency: Mapped[str | None] = mapped_column(String(8))
    location: Mapped[str | None] = mapped_column(String(255), index=True)
    event_date: Mapped[str | None] = mapped_column(String(64))

    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, native_enum=False, length=16), default=LeadStatus.NEW, nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="leads")
    classification: Mapped["LeadClassification | None"] = relationship(
        back_populates="lead", uselist=False, cascade="all, delete-orphan"
    )


class LeadClassification(Base, TimestampMixin):
    __tablename__ = "lead_classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    intent: Mapped[IntentLabel] = mapped_column(
        Enum(IntentLabel, native_enum=False, length=16), nullable=False, index=True
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    # Human-readable reason tags, e.g. ["strong buy phrase: 'ready to buy'", "contact info present"]
    reasons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Raw extraction payload {product, price, currency, date, location}
    extracted: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Which classifier produced this: "rules" | "claude:<model>" | "openai:<model>"
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="rules")
    # Stage-1 rule signal dump for debugging/audit
    rule_signals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="classification")
