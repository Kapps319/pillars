from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbDep, UserDep
from app.core.crypto import encrypt_value, mask_secret
from app.models import AuditLog, Integration
from app.schemas.integration import IntegrationCreate, IntegrationOut

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=list[IntegrationOut])
def list_integrations(db: DbDep, user: UserDep) -> list[Integration]:
    return db.query(Integration).filter(Integration.user_id == user.id).order_by(Integration.provider).all()


@router.post("", response_model=IntegrationOut, status_code=status.HTTP_201_CREATED)
def upsert_integration(payload: IntegrationCreate, db: DbDep, user: UserDep) -> Integration:
    """Create or update (by key_name) an API key. Values are encrypted at rest
    and never returned in plaintext — only a masked preview.
    """
    integration = (
        db.query(Integration)
        .filter(Integration.user_id == user.id, Integration.key_name == payload.key_name)
        .first()
    )
    if integration is None:
        integration = Integration(user_id=user.id, provider=payload.provider, key_name=payload.key_name,
                                  encrypted_value="", masked_value="")
        db.add(integration)
    integration.provider = payload.provider
    integration.encrypted_value = encrypt_value(payload.value)
    integration.masked_value = mask_secret(payload.value)
    db.add(
        AuditLog(user_id=user.id, action="integration.upsert", entity_type="integration", meta={"key": payload.key_name})
    )
    db.commit()
    db.refresh(integration)
    return integration


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(integration_id: int, db: DbDep, user: UserDep) -> None:
    integration = db.get(Integration, integration_id)
    if integration is None or integration.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    db.delete(integration)
    db.add(
        AuditLog(user_id=user.id, action="integration.delete", entity_type="integration", entity_id=str(integration_id))
    )
    db.commit()
