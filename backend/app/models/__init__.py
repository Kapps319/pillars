"""ORM models. Import everything here so Alembic autogenerate sees all tables."""

from app.models.audit import AuditLog
from app.models.campaign import Campaign
from app.models.enums import IntentLabel, IntentTarget, JobStatus, LeadStatus
from app.models.integration import Integration
from app.models.job import ScrapingJob
from app.models.lead import Lead, LeadClassification
from app.models.source import SearchSource
from app.models.user import User

__all__ = [
    "AuditLog",
    "Campaign",
    "IntentLabel",
    "IntentTarget",
    "Integration",
    "JobStatus",
    "Lead",
    "LeadClassification",
    "LeadStatus",
    "ScrapingJob",
    "SearchSource",
    "User",
]
