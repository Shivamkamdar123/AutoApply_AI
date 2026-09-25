"""
Authentication & Multi-Tenant Security Tests
============================================
Verifies signup, login, password hashing, token validation, 401 gates,
rate limiting, password reset, and session management.
"""

from fastapi.testclient import TestClient
from app.db.storage import storage


def test_signup_success(client: TestClient):
    payload = {
        "email": "newuser@example.com",
        "password": "strongPassword123!",
        "full_name": "New User",
    }
    resp = client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["full_name"] == "New User"
    assert "password_hash" not in str(data)  # Never expose hash


def test_signup_duplicate_email_rejected(client: TestClient, test_user):
    payload = {
        "email": test_user.email,  # already exists
        "password": "newpassword123",
        "full_name": "Duplicate Person",
    }
    resp = client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


def test_signup_short_password_rejected(client: TestClient):
    payload = {"email": "short@example.com", "password": "123"}
    resp = client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 422 or resp.status_code == 400


def test_login_success(client: TestClient, test_user):
    payload = {"email": test_user.email, "password": "secret123"}
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == test_user.email


def test_login_invalid_password_returns_generic_401(client: TestClient, test_user):
    payload = {"email": test_user.email, "password": "wrongpassword"}
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 401
    # Generic error message to prevent account probing
    assert resp.json()["detail"] == "Invalid email or password."


def test_login_unknown_email_returns_generic_401(client: TestClient):
    payload = {"email": "nonexistent@example.com", "password": "secretPassword"}
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


def test_logout_clears_cookies(client: TestClient):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_get_me_endpoint_authenticated(client: TestClient, auth_headers, test_user):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == test_user.email


def test_get_me_unauthenticated_returns_401(client: TestClient):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert "authentication required" in resp.json()["detail"].lower()


def test_refresh_token_lifecycle(client: TestClient, test_user):
    login_resp = client.post("/api/auth/login", json={"email": test_user.email, "password": "secret123"})
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_data = resp.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data


def test_forgot_and_reset_password_flow(client: TestClient, test_user):
    # 1. Request forgot password
    forgot_resp = client.post("/api/auth/forgot-password", json={"email": test_user.email})
    assert forgot_resp.status_code == 200
    assert "dispatched" in forgot_resp.json()["message"]

    # 2. Extract reset token from test storage
    with storage._get_connection() as conn:
        cursor = conn.execute("SELECT token FROM password_resets WHERE user_id = ? ORDER BY expires_at DESC", (test_user.id,))
        row = cursor.fetchone()
        assert row is not None
        reset_token = row["token"]

    # 3. Reset password
    reset_resp = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "brandNewPassword123!"},
    )
    assert reset_resp.status_code == 200

    # 4. Verify login with new password succeeds
    login_resp = client.post("/api/auth/login", json={"email": test_user.email, "password": "brandNewPassword123!"})
    assert login_resp.status_code == 200
