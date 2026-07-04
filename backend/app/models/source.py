from __future__ import annotations

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SearchSource(Base, TimestampMixin):
    """DB record of a source adapter (mirrors the code registry).

    `enabled` lets a user switch a source off without env changes; a source is
    only used when it's enabled here AND its adapter reports available().
    """

    __tablename__ = "search_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Names of env vars / integration keys the adapter needs, e.g. ["REDDIT_CLIENT_ID"]
    required_keys: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
