"""
Integration tests for API routes
=================================
Tests resume upload, job matching, review queue actions, dashboard summary,
and strict multi-tenant data isolation between accounts.
"""

from fastapi.testclient import TestClient
from app.models.schemas import ApplicationStatus, FieldMappingDecision
from app.db.storage import storage


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_match_jobs_endpoint(client: TestClient, auth_headers):
    response = client.get("/api/jobs/match", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert isinstance(data["matches"], list)
    assert len(data["matches"]) > 0
    first = data["matches"][0]
    assert "score" in first
    assert "job" in first
    assert "recommended" in first
    # Per-source telemetry present
    assert "sources_status" in data


def test_dashboard_summary_endpoint(client: TestClient, auth_headers):
    response = client.get("/api/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_matched" in data
    assert "total_applied" in data
    assert "total_needs_review" in data
    assert "average_match_score" in data
    assert "dry_run_mode" in data


def test_review_queue_and_action(client: TestClient, auth_headers):
    # Fetch review queue for authenticated user
    res_queue = client.get("/api/review-queue", headers=auth_headers)
    assert res_queue.status_code == 200
    queue = res_queue.json()
    assert isinstance(queue, list)
    assert len(queue) > 0

    first_item = queue[0]
    job_id = first_item["job_id"]

    # Approve application in dry-run
    res_action = client.post(
        f"/api/review-queue/{job_id}/action",
        json={"job_id": job_id, "action": "approve", "auto_submit_override": False},
        headers=auth_headers,
    )
    assert res_action.status_code == 200
    updated = res_action.json()
    assert updated["stage"] == "applied"
    assert updated["dry_run"] is True


def test_resume_upload_endpoint(client: TestClient, auth_headers):
    resume_content = (
        b"Jane Candidate\n"
        b"jane@example.com | +1 (555) 456-7890\n"
        b"Python Developer with FastAPI, SQL, and Docker experience (2020 - 2024)."
    )
    files = {"file": ("test_resume.txt", resume_content, "text/plain")}
    response = client.post("/api/resume/upload", files=files, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Jane Candidate"
    assert data["email"] == "jane@example.com"
    assert "python" in data["skills"]


def test_resume_upload_invalid_extension(client: TestClient, auth_headers):
    files = {"file": ("malicious.exe", b"binary", "application/octet-stream")}
    response = client.post("/api/resume/upload", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_multi_tenant_data_isolation(client: TestClient, auth_headers, auth_headers_b, test_user, test_user_b):
    """Verifies User A cannot see or mutate User B's applications or review queue."""
    # Seed application specifically for User A
    app_a = ApplicationStatus(
        job_id="job-private-a",
        user_id=test_user.id,
        company="User A Inc",
        title="Private Role A",
        stage="needs_review",
        match_score=0.92,
        updated_at="2026-09-25T12:00:00Z",
        dry_run=True,
        notes="Private application for User A only",
    )
    storage.save_or_update_application(app_a, user_id=test_user.id)

    # 1. User A lists applications: includes job-private-a
    apps_a = client.get("/api/applications", headers=auth_headers).json()
    job_ids_a = [a["job_id"] for a in apps_a]
    assert "job-private-a" in job_ids_a

    # 2. User B lists applications: CANNOT see job-private-a
    apps_b = client.get("/api/applications", headers=auth_headers_b).json()
    job_ids_b = [b["job_id"] for b in apps_b]
    assert "job-private-a" not in job_ids_b

    # 3. User B attempts to approve User A's application: returns 404
    resp_tamper = client.post(
        "/api/review-queue/job-private-a/action",
        json={"job_id": "job-private-a", "action": "approve"},
        headers=auth_headers_b,
    )
    assert resp_tamper.status_code == 404
