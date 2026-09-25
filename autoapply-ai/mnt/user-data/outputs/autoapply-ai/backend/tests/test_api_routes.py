"""
Integration tests for API routes
=================================
Tests resume upload, job matching, review queue actions, and dashboard summary.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_match_jobs_endpoint(client: TestClient):
    response = client.get("/api/jobs/match")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "score" in first
    assert "job" in first
    assert "recommended" in first


def test_dashboard_summary_endpoint(client: TestClient):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_matched" in data
    assert "total_applied" in data
    assert "total_needs_review" in data
    assert "average_match_score" in data
    assert "dry_run_mode" in data


def test_review_queue_and_action(client: TestClient):
    # Fetch review queue
    res_queue = client.get("/api/review-queue")
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
    )
    assert res_action.status_code == 200
    updated = res_action.json()
    assert updated["stage"] == "applied"
    assert updated["dry_run"] is True


def test_resume_upload_endpoint(client: TestClient):
    resume_content = (
        b"Jane Candidate\n"
        b"jane@example.com | +1 (555) 456-7890\n"
        b"Python Developer with FastAPI, SQL, and Docker experience (2020 - 2024)."
    )
    files = {"file": ("test_resume.txt", resume_content, "text/plain")}
    response = client.post("/api/resume/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Jane Candidate"
    assert data["email"] == "jane@example.com"
    assert "python" in data["skills"]


def test_resume_upload_invalid_extension(client: TestClient):
    files = {"file": ("malicious.exe", b"binary", "application/octet-stream")}
    response = client.post("/api/resume/upload", files=files)
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()
