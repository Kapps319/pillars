"""Celery application. Broker/result backend is Redis (REDIS_URL)."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "leadfinder",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    # Fail fast when the broker is down so the API's sync fallback kicks in
    broker_transport_options={"max_retries": 1, "socket_connect_timeout": 2},
)
