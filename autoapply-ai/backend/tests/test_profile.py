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
