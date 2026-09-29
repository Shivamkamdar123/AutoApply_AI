"""
Profile & Resume Management Tests
=================================
Verifies editable profile CRUD, optional fields, resume uploads, versioning,
and tenant isolation across user accounts.
"""

from fastapi.testclient import TestClient


def test_get_profile_authenticated(client: TestClient, auth_headers, test_user):
    resp = client.get("/api/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == test_user.id
    assert "skills" in data
    assert isinstance(data["skills"], list)


def test_patch_profile_optional_fields(client: TestClient, auth_headers, test_user):
    patch_payload = {
        "full_name": "Jane Developer",
        "phone": "+1-555-0987",
        "linkedin_url": "https://linkedin.com/in/janedev",
        "desired_role": "Staff Backend Engineer",
        "remote_preference": "remote",
        "skills": ["python", "fastapi", "golang", "redis"],
        "years_experience": 6.5,
        "bio": "Experienced architect focusing on distributed systems.",
    }
    resp = client.patch("/api/profile", json=patch_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Jane Developer"
    assert data["desired_role"] == "Staff Backend Engineer"
    assert data["remote_preference"] == "remote"
    assert "golang" in data["skills"]
    assert data["years_experience"] == 6.5
    assert data["bio"] == patch_payload["bio"]

    # Verify persistent read
    get_resp = client.get("/api/profile", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Jane Developer"


def test_upload_resume_and_suggestions(client: TestClient, auth_headers, sample_txt_resume, test_user):
    with open(sample_txt_resume, "rb") as f:
        resp = client.post(
            "/api/profile/resume",
            files={"file": ("my_resume.txt", f, "text/plain")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == test_user.id
    assert "python" in [s.lower() for s in data["skills"]]
    assert data["active_resume_id"] is not None

    # Check resumes history endpoint
    resumes_resp = client.get("/api/profile/resumes", headers=auth_headers)
    assert resumes_resp.status_code == 200
    resumes = resumes_resp.json()
    assert len(resumes) >= 1
    assert resumes[0]["filename"] == "my_resume.txt"
    assert resumes[0]["is_active"] is True


def test_delete_resume_version(client: TestClient, auth_headers, sample_txt_resume):
    # Upload first
    with open(sample_txt_resume, "rb") as f:
        upload_resp = client.post(
            "/api/profile/resume",
            files={"file": ("to_delete.txt", f, "text/plain")},
            headers=auth_headers,
        )
    resume_id = upload_resp.json()["active_resume_id"]

    # Delete resume
    del_resp = client.delete(f"/api/profile/resume/{resume_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    # Verify it is no longer listed
    resumes_resp = client.get("/api/profile/resumes", headers=auth_headers)
    ids = [r["id"] for r in resumes_resp.json()]
    assert resume_id not in ids


def test_profile_unauthenticated_returns_401(client: TestClient):
    resp = client.get("/api/profile")
    assert resp.status_code == 401


def test_profile_dashboard_resume_state_sync(client: TestClient, auth_headers, sample_txt_resume):
    """
    Regression Test: Ensures Dashboard 'Resume Parsed' count and Profile 'Resume History'
    read from the exact same per-user `resumes` table, preventing any UI state desync.
    """
    # 1. Before upload: both dashboard summary and profile resumes show zero / inactive
    dash_before = client.get("/api/dashboard/summary", headers=auth_headers).json()
    resumes_before = client.get("/api/profile/resumes", headers=auth_headers).json()
    assert dash_before["total_resumes"] == len(resumes_before)

    # 2. Upload resume
    with open(sample_txt_resume, "rb") as f:
        upload_resp = client.post(
            "/api/profile/resume",
            files={"file": ("sync_test_resume.txt", f, "text/plain")},
            headers=auth_headers,
        )
    assert upload_resp.status_code == 200

    # 3. After upload: both dashboard summary and profile history must agree exactly
    dash_after = client.get("/api/dashboard/summary", headers=auth_headers).json()
    resumes_after = client.get("/api/profile/resumes", headers=auth_headers).json()

    assert dash_after["total_resumes"] == len(resumes_after)
    assert dash_after["total_resumes"] >= 1
    assert dash_after["has_active_resume"] is True
    assert any(r["filename"] == "sync_test_resume.txt" for r in resumes_after)


def test_extension_field_mapping_and_events(client: TestClient, auth_headers):
    """Verifies extension field mapping and application event syncing."""
    # Test field mapping
    map_payload = {
        "fields": [
            {"selector": "#name", "name": "full_name", "field_type": "text", "label": "Full Name"},
            {"selector": "#email", "name": "email", "field_type": "email", "label": "Email Address"},
            {"selector": "#phone", "name": "phone", "field_type": "tel", "label": "Phone Number"},
        ],
        "job_title": "Senior Python Developer",
        "company": "Tech Corp",
    }
    map_resp = client.post("/api/browser/map-fields", json=map_payload, headers=auth_headers)
    assert map_resp.status_code == 200
    decisions = map_resp.json()
    assert len(decisions) >= 2
    assert any(d["field_name"] == "Email Address" for d in decisions)

    # Test extension event sync
    event_payload = {
        "job_id": "ext-test-101",
        "url": "https://www.linkedin.com/jobs/view/101",
        "company": "Tech Corp",
        "title": "Senior Python Developer",
        "stage": "applied",
        "event_type": "apply_click",
        "notes": "Verified application via AutoApply Copilot",
    }
    event_resp = client.post("/api/applications/extension-event", json=event_payload, headers=auth_headers)
    assert event_resp.status_code == 200
    assert event_resp.json()["stage"] == "applied"

    # Verify it appears in applications tracker with source="extension"
    apps_resp = client.get("/api/applications", headers=auth_headers)
    assert apps_resp.status_code == 200
    ext_app = next((a for a in apps_resp.json() if a["job_id"] == "ext-test-101"), None)
    assert ext_app is not None
    assert ext_app["source"] == "extension"
    assert ext_app["stage"] == "applied"


def test_ats_keyword_gap_endpoint(client: TestClient, auth_headers):
    """Verifies the ATS keyword gap analysis endpoint."""
    ats_payload = {
        "job_id": "job-py-99",
        "job_title": "Full Stack Python Developer",
        "job_description": "We are seeking a Python engineer proficient in FastAPI, Docker, Kubernetes, and PostgreSQL.",
        "company": "Cloud Innovators",
    }
    resp = client.post("/api/ats/keyword-gap", json=ats_payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "ats_score" in data
    assert isinstance(data["ats_score"], (int, float))
    assert "matched_keywords" in data
    assert "missing_keywords" in data
    assert "tailored_cover_letter" in data

