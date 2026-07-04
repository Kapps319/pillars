from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Integration(Base, TimestampMixin):
    """A user-provided API key/secret, encrypted at rest (Fernet, see core/crypto.py).

    Env vars always take precedence; integrations let a user add keys from the
    UI without redeploying.
    """

    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("user_id", "key_name", name="uq_integration_user_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # Provider grouping for the UI: "reddit" | "google" | "anthropic" | "openai" | "twitter"
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Env-style key name, e.g. "REDDIT_CLIENT_ID"
    key_name: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    masked_value: Mapped[str] = mapped_column(String(64), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="integrations")
