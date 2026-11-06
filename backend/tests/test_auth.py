from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_session
from app.core.jwt import create_access_token
from app.main import app
from app.models.refresh_session import RefreshSession
from app.models.user import User


@pytest.fixture
def client(monkeypatch, session):
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-" * 5)
    monkeypatch.setattr(settings, "auth_cookie_secure", True)
    monkeypatch.setattr(settings, "auth_allowed_origins", ["http://localhost:5173"])
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(
            app,
            base_url="https://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()


def register(client):
    return client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "a-good-password",
        },
    )


def test_register_login_and_access(client):
    browser, session = client
    response = register(browser)
    assert response.status_code == 201
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "secure" in response.headers["set-cookie"].lower()
    assert response.headers["cache-control"] == "no-store"
    token = response.json()["access_token"]
    assert (
        browser.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()[
            "name"
        ]
        == "Test User"
    )
    stored = session.scalar(select(RefreshSession))
    assert stored.token_hash != browser.cookies.get("refresh_token")
    assert register(browser).status_code == 409
    assert (
        browser.post(
            "/auth/login", data={"username": "test@example.com", "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        browser.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "a-good-password"},
        ).status_code
        == 200
    )


def test_rotation_reuse_revokes_family(client):
    browser, _ = client
    register(browser)
    original = browser.cookies.get("refresh_token")
    assert browser.post("/auth/refresh").status_code == 200
    replacement = browser.cookies.get("refresh_token")
    assert replacement != original
    browser.cookies.clear()
    browser.cookies.set("refresh_token", original)
    assert browser.post("/auth/refresh").status_code == 401
    browser.cookies.clear()
    browser.cookies.set("refresh_token", replacement)
    assert browser.post("/auth/refresh").status_code == 401


def test_logout_and_origin_protection(client):
    browser, _ = client
    register(browser)
    token = browser.cookies.get("refresh_token")
    assert (
        browser.post(
            "/auth/refresh", headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert browser.post("/auth/logout").status_code == 204
    assert not browser.cookies.get("refresh_token")
    browser.cookies.set("refresh_token", token)
    assert browser.post("/auth/refresh").status_code == 401


def test_expiry_and_invalid_tokens(client):
    browser, session = client
    assert browser.post("/auth/refresh").status_code == 401
    register(browser)
    record = session.scalar(
        select(RefreshSession).join(User).where(User.email == "test@example.com")
    )
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert browser.post("/auth/refresh").status_code == 401
    user = session.scalar(select(User).where(User.email == "test@example.com"))
    for token in [
        "invalid",
        create_access_token({}),
        create_access_token({"sub": "invalid"}),
        create_access_token({"sub": "2147483647"}),
        create_access_token({"sub": str(user.id)}, timedelta(seconds=-1)),
    ]:
        assert (
            browser.get(
                "/auth/me", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 401
        )


def test_registration_always_creates_producer(client):
    browser, session = client
    response = browser.post(
        "/auth/register",
        json={
            "name": "Productor",
            "email": "producer@example.com",
            "password": "a-good-password",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    user = session.scalar(select(User).where(User.email == "producer@example.com"))
    assert user.role.value == "producer"


def test_email_is_stored_and_matched_in_lowercase(client):
    browser, session = client
    data = {"name": "Ana", "email": "Ana@Example.com", "password": "a-good-password"}
    assert browser.post("/auth/register", json=data).status_code == 201
    assert (
        session.scalar(select(User).where(User.email == "ana@example.com")).email
        == "ana@example.com"
    )
    data["email"] = "ana@example.com"
    assert browser.post("/auth/register", json=data).status_code == 409
    for email in ["ana@example.com", "ANA@EXAMPLE.COM"]:
        assert (
            browser.post(
                "/auth/login", data={"username": email, "password": data["password"]}
            ).status_code
            == 200
        )
