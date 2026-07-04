from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import IntentTarget

if TYPE_CHECKING:
    from app.models.job import ScrapingJob
    from app.models.lead import Lead
    from app.models.user import User


class Campaign(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The product/market the user plugs in — e.g. "F1 tickets", "MacBook Pro", "apartment in Dubai"
    product_keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    intent_target: Mapped[IntentTarget] = mapped_column(
        Enum(IntentTarget, native_enum=False, length=16), default=IntentTarget.BOTH, nullable=False
    )
    location: Mapped[str | None] = mapped_column(String(255))
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    min_confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # List of source adapter keys this campaign scans, e.g. ["mock", "reddit"]
    sources: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="campaigns")
    leads: Mapped[list["Lead"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    jobs: Mapped[list["ScrapingJob"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
