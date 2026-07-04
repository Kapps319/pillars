"""Shared enums. Stored as plain strings (native_enum=False) for portability."""

from __future__ import annotations

import enum


class IntentLabel(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    MENTION = "MENTION"
    SPAM = "SPAM"


class IntentTarget(str, enum.Enum):
    """What a campaign is hunting for."""

    BUYERS = "BUYERS"
    SELLERS = "SELLERS"
    BOTH = "BOTH"


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    SAVED = "SAVED"
    CONTACTED = "CONTACTED"
    REJECTED = "REJECTED"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
