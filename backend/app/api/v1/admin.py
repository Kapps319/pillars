from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import UserDep
from app.classifier.llm import get_llm_client
from app.core.config import get_settings
from app.schemas.integration import AdminSettingsOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings", response_model=AdminSettingsOut)
def get_admin_settings(user: UserDep) -> AdminSettingsOut:
    """Effective runtime configuration (safe fields only, no secrets)."""
    settings = get_settings()
    client = get_llm_client(settings)
    return AdminSettingsOut(
        llm_provider=settings.llm_provider,
        llm_available=client.name == settings.llm_provider or settings.llm_provider == "rules",
        llm_model=getattr(client, "model_id", client.name),
        search_backend=settings.search_backend,
        celery_enabled=settings.celery_enabled,
        sources_enabled=settings.enabled_source_keys,
        environment=settings.environment,
    )
