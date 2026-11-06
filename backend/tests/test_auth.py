from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.db import get_session
from app.core.jwt import create_access_token
from app.main import app
from app.models.refresh_session import RefreshSession
from app.models.user import User


@pytest.fixture(scope="session", autouse=True)
def database():
    """These API tests need only the authentication tables, without PostGIS."""
    yield


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "test-secret-" * 5)
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    User.__table__.create(engine)
    RefreshSession.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        app.dependency_overrides[get_session] = lambda: session
        with TestClient(
            app,
            base_url="https://testserver",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            yield client, session
        app.dependency_overrides.clear()
    engine.dispose()


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


def test_expiry_disabled_user_and_invalid_tokens(client):
    browser, session = client
    assert browser.post("/auth/refresh").status_code == 401
    register(browser)
    record = session.scalar(select(RefreshSession))
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert browser.post("/auth/refresh").status_code == 401
    login = browser.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "a-good-password"},
    )
    user = session.scalar(select(User))
    user.is_active = False
    session.commit()
    assert browser.post("/auth/refresh").status_code == 401
    assert (
        browser.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        ).status_code
        == 401
    )
    user.is_active = True
    session.commit()
    for token in [
        "invalid",
        create_access_token({"sub": str(user.id)}, timedelta(seconds=-1)),
    ]:
        assert (
            browser.get(
                "/auth/me", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 401
        )
