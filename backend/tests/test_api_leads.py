from __future__ import annotations

import pytest

from app.classifier.llm.rules_client import RulesOnlyClient
from app.models import Campaign, JobStatus, ScrapingJob, User
from app.services.scraping import execute_job, ingest_post
from app.sources.base import SearchFilters
from app.sources.mock_source import MockSource


@pytest.fixture()
def seeded_campaign(client, db, auth_headers):
    """Create a campaign via the API and ingest all mock fixtures into it."""
    response = client.post(
        "/api/v1/campaigns",
        headers=auth_headers,
        json={"name": "Test radar", "product_keyword": "tickets", "sources": ["mock"]},
    )
    assert response.status_code == 201
    campaign_id = response.json()["id"]
    campaign = db.get(Campaign, campaign_id)
    llm = RulesOnlyClient()
    for post in MockSource().search("", SearchFilters(limit=100)):
        ingest_post(db, campaign, post, llm)
    db.commit()
    return campaign_id


def test_campaign_crud(client, auth_headers):
    response = client.post(
        "/api/v1/campaigns",
        headers=auth_headers,
        json={"name": "CRUD", "product_keyword": "watches", "intent_target": "BUYERS", "min_confidence": 20},
    )
    assert response.status_code == 201
    cid = response.json()["id"]

    response = client.patch(f"/api/v1/campaigns/{cid}", headers=auth_headers, json={"location": "Dubai"})
    assert response.status_code == 200
    assert response.json()["location"] == "Dubai"

    response = client.get("/api/v1/campaigns", headers=auth_headers)
    assert any(c["id"] == cid for c in response.json())

    response = client.delete(f"/api/v1/campaigns/{cid}", headers=auth_headers)
    assert response.status_code == 204
    response = client.get(f"/api/v1/campaigns/{cid}", headers=auth_headers)
    assert response.status_code == 404  # soft-deleted


def test_leads_filters_sort_pagination(client, auth_headers, seeded_campaign):
    # unfiltered
    response = client.get("/api/v1/leads", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 25

    # intent filter
    response = client.get("/api/v1/leads?intent=BUY", headers=auth_headers)
    assert all(item["classification"]["intent"] == "BUY" for item in response.json()["items"])

    # min_score filter + sort ascending
    response = client.get("/api/v1/leads?min_score=70&sort_by=score&sort_dir=asc", headers=auth_headers)
    scores = [item["score"] for item in response.json()["items"]]
    assert all(s >= 70 for s in scores)
    assert scores == sorted(scores)

    # text search (ILIKE fallback on SQLite)
    response = client.get("/api/v1/leads?q=World+Cup", headers=auth_headers)
    assert response.json()["total"] >= 1

    # location filter
    response = client.get("/api/v1/leads?location=Dubai", headers=auth_headers)
    assert all("dubai" in (item["location"] or "").lower() for item in response.json()["items"])

    # pagination
    response = client.get("/api/v1/leads?page_size=5&page=2", headers=auth_headers)
    body = response.json()
    assert body["page"] == 2
    assert len(body["items"]) <= 5


def test_lead_detail_and_status_update(client, auth_headers, seeded_campaign):
    lead = client.get("/api/v1/leads?page_size=1", headers=auth_headers).json()["items"][0]
    response = client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["classification"]["reasons"]

    response = client.patch(
        f"/api/v1/leads/{lead['id']}/status", headers=auth_headers, json={"status": "SAVED"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SAVED"

    response = client.get("/api/v1/leads?status=SAVED", headers=auth_headers)
    assert response.json()["total"] == 1


def test_csv_export(client, auth_headers, seeded_campaign):
    response = client.get("/api/v1/leads/export.csv?intent=BUY", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("id,campaign,source,intent")
    assert len(lines) >= 2


def test_dashboard_stats(client, auth_headers, seeded_campaign):
    response = client.get("/api/v1/leads/stats", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_leads"] >= 25
    assert set(body["by_intent"]) <= {"BUY", "SELL", "MENTION", "SPAM"}
    assert len(body["recent_leads"]) <= 5


def test_leads_are_scoped_to_owner(client, auth_headers, seeded_campaign):
    client.post("/api/v1/auth/register", json={"email": "other@example.com", "password": "password123"})
    other_token = client.post(
        "/api/v1/auth/login", json={"email": "other@example.com", "password": "password123"}
    ).json()["access_token"]
    response = client.get("/api/v1/leads", headers={"Authorization": f"Bearer {other_token}"})
    assert response.json()["total"] == 0


def test_execute_job_dedupes_and_records_stats(db):
    user = User(email="job@example.com", hashed_password="x")
    db.add(user)
    db.flush()
    campaign = Campaign(user_id=user.id, name="Job test", product_keyword="tickets", sources=["mock", "reddit"])
    db.add(campaign)
    db.flush()
    job = ScrapingJob(campaign_id=campaign.id)
    db.add(job)
    db.commit()

    execute_job(db, job.id)
    db.refresh(job)
    assert job.status == JobStatus.SUCCESS
    assert job.stats["mock"]["created"] > 0
    # reddit has no keys in tests -> reported as skipped, never crashes
    assert "skipped" in job.stats.get("reddit", {})

    created_first = job.stats["mock"]["created"]
    job2 = ScrapingJob(campaign_id=campaign.id)
    db.add(job2)
    db.commit()
    execute_job(db, job2.id)
    db.refresh(job2)
    assert job2.stats["mock"]["created"] == 0  # dedupe on re-run
    assert created_first > 0
