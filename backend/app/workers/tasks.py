from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.run_scraping_job_task", bind=True, max_retries=1)
def run_scraping_job_task(self, job_id: int, urls: list[str] | None = None) -> None:
    # Imported here so the Celery worker only pulls the app stack when running a task
    from app.services.scraping import run_job_standalone

    run_job_standalone(job_id, urls)
