from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, auth, campaigns, health, integrations, jobs, leads, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(campaigns.router)
api_router.include_router(jobs.router)
api_router.include_router(leads.router)
api_router.include_router(sources.router)
api_router.include_router(integrations.router)
api_router.include_router(admin.router)
