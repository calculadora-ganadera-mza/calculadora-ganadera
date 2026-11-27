import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_session
from app.core.password import hash_password
from app.main import app
from app.models import PasswordResetCode, RefreshSession, User
from app.services.auth import token_hash

CODE = "123456"
OTHER_CODE = "654321"
OLD_PASSWORD = "old-password-123"
NEW_PASSWORD = "new-password-456"


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
        app.dependency_overrides.pop(get_session, None)


def create_user(session, email="ana@example.com", verified=False) -> User:
    user = User(
        name="Ana",
        email=email,
        password_hash=hash_password(OLD_PASSWORD),
        email_verified=verified,
    )
    session.add(user)
    session.flush()
    return user


def add_code(session, user, code=CODE, **fields) -> PasswordResetCode:
    """Guarda un código conocido, vigente salvo que se indique otro vencimiento."""
    fields.setdefault("expires_at", datetime.now(UTC) + timedelta(minutes=15))
    record = PasswordResetCode(user_id=user.id, code_hash=token_hash(code), **fields)
    session.add(record)
    session.flush()
    return record


def forgot(browser, email="ana@example.com"):
    return browser.post("/auth/forgot-password", json={"email": email})


def reset(browser, email="ana@example.com", code=CODE, password=NEW_PASSWORD):
    return browser.post(
        "/auth/reset-password",
        json={"email": email, "code": code, "password": password},
    )


def login(browser, email="ana@example.com", password=NEW_PASSWORD):
    return browser.post("/auth/login", data={"username": email, "password": password})


def test_forgot_password_mails_hashed_code_for_existing_user(client, outbox):
    browser, session = client
    user = create_user(session)

    response = forgot(browser, "ANA@EXAMPLE.COM")

    assert response.status_code == 202
    assert response.content == b""
    [(to, subject, text)] = outbox
    assert to == user.email
    assert "recuperar" in subject.lower()
    [code] = re.findall(r"\b\d{6}\b", text)
    stored = session.scalar(
        select(PasswordResetCode).where(PasswordResetCode.user_id == user.id)
    )
    assert stored is not None
    assert stored.code_hash != code
    assert stored.code_hash == token_hash(code)


def test_forgot_password_returns_same_response_for_unknown_email(client, outbox):
    browser, session = client
    create_user(session)

    registered = forgot(browser, "ana@example.com")
    # Vacía la bandeja para comprobar que el correo inexistente no envía nada.
    outbox.clear()
    unknown = forgot(browser, "noexiste@example.com")

    assert unknown.status_code == registered.status_code == 202
    assert unknown.content == registered.content == b""
    assert outbox == []


def test_forgot_password_respects_cooldown_and_hourly_limit_silently(client, outbox):
    browser, session = client
    user = create_user(session)
    first = add_code(session, user)

    # Dentro de los 60s de espera responde 202 igual y no envía ni pisa el código.
    response = forgot(browser)
    assert response.status_code == 202
    assert response.content == b""
    assert outbox == []
    assert reset(browser, code=CODE).status_code == 204

    # Pasada la espera, si llegó al tope por hora también responde 202 sin enviar.
    two_minutes_ago = datetime.now(UTC) - timedelta(minutes=2)
    first.created_at = two_minutes_ago
    for _ in range(settings.password_reset_codes_per_hour - 1):
        add_code(session, user, created_at=two_minutes_ago)
    session.flush()

    assert forgot(browser).status_code == 202
    assert outbox == []


def test_codes_older_than_an_hour_do_not_count(client, outbox):
    browser, session = client
    user = create_user(session)
    over_an_hour_ago = datetime.now(UTC) - timedelta(minutes=61)
    for _ in range(settings.password_reset_codes_per_hour):
        add_code(session, user, created_at=over_an_hour_ago)

    assert forgot(browser).status_code == 202
    assert len(outbox) == 1


def test_reset_password_updates_password_verifies_email_and_does_not_login(
    client, outbox
):
    browser, session = client
    user = create_user(session, verified=False)
    assert forgot(browser).status_code == 202
    [(_, _, text)] = outbox
    [code] = re.findall(r"\b\d{6}\b", text)

    response = reset(browser, email="ANA@EXAMPLE.COM", code=code, password=NEW_PASSWORD)

    assert response.status_code == 204
    assert "set-cookie" not in response.headers
    session.refresh(user)
    assert user.email_verified is True
    assert login(browser, password=OLD_PASSWORD).status_code == 401
    assert login(browser, password=NEW_PASSWORD).status_code == 200


def test_reset_password_revokes_all_open_sessions(client):
    browser, session = client
    user = create_user(session)

    # Inicia sesión en dos dispositivos distintos.
    assert login(browser, password=OLD_PASSWORD).status_code == 200
    device_one_refresh = browser.cookies.get("refresh_token")
    browser.cookies.clear()
    assert login(browser, password=OLD_PASSWORD).status_code == 200
    device_two_refresh = browser.cookies.get("refresh_token")
    assert device_one_refresh != device_two_refresh

    add_code(session, user)
    assert reset(browser).status_code == 204

    for refresh_token in (device_one_refresh, device_two_refresh):
        browser.cookies.clear()
        browser.cookies.set("refresh_token", refresh_token)
        assert browser.post("/auth/refresh").status_code == 401

    assert (
        session.scalar(
            select(RefreshSession).where(
                RefreshSession.user_id == user.id, RefreshSession.revoked.is_(False)
            )
        )
        is None
    )


def test_only_latest_code_is_valid(client):
    browser, session = client
    user = create_user(session)
    add_code(session, user, CODE)
    add_code(session, user, OTHER_CODE)

    assert reset(browser, code=CODE).status_code == 422
    assert reset(browser, code=OTHER_CODE).status_code == 204


def test_code_can_only_be_used_once(client):
    browser, session = client
    user = create_user(session)
    add_code(session, user, CODE)

    assert reset(browser, code=CODE, password=NEW_PASSWORD).status_code == 204
    assert reset(browser, code=CODE, password="another-password-789").status_code == 422
    assert login(browser, password="another-password-789").status_code == 401
    assert login(browser, password=NEW_PASSWORD).status_code == 200


def test_expired_used_exhausted_and_missing_codes_share_same_error(client):
    browser, session = client
    user = create_user(session)

    # Sin código emitido
    no_code_resp = reset(browser)

    # Código incorrecto habiendo uno vigente
    add_code(session, user, CODE)
    wrong_code_resp = reset(browser, code=OTHER_CODE)

    # Código vencido
    add_code(session, user, expires_at=datetime.now(UTC) - timedelta(seconds=1))
    expired_resp = reset(browser)

    # Código agotado por intentos
    add_code(session, user, attempts=settings.password_reset_code_max_attempts)
    exhausted_resp = reset(browser)

    # Código ya usado en un cambio exitoso
    add_code(session, user, CODE)
    assert reset(browser, code=CODE).status_code == 204
    used_resp = reset(browser, code=CODE)

    # Correo inexistente
    unknown_user_resp = reset(browser, email="noexiste@example.com")

    responses = [
        no_code_resp,
        wrong_code_resp,
        expired_resp,
        exhausted_resp,
        used_resp,
        unknown_user_resp,
    ]
    assert all(r.status_code == 422 for r in responses)
    details = {r.json()["detail"] for r in responses}
    assert len(details) == 1


def test_sixth_attempt_is_rejected_even_with_correct_code_and_account_stays_unlocked(
    client,
):
    browser, session = client
    user = create_user(session)
    record = add_code(session, user)

    for _ in range(settings.password_reset_code_max_attempts):
        resp = reset(browser, code=OTHER_CODE)
        assert resp.status_code == 422

    # Al sexto intento se rechaza aunque el código sea el correcto.
    sixth = reset(browser, code=CODE)
    assert sixth.status_code == 422

    session.rollback()
    session.refresh(record)
    assert record.attempts == settings.password_reset_code_max_attempts

    # Los intentos fallidos no bloquean la cuenta.
    assert login(browser, password=OLD_PASSWORD).status_code == 200


def test_fifth_attempt_with_correct_code_succeeds(client):
    browser, session = client
    user = create_user(session)
    add_code(session, user)

    for _ in range(settings.password_reset_code_max_attempts - 1):
        assert reset(browser, code=OTHER_CODE).status_code == 422

    assert reset(browser, code=CODE).status_code == 204


def test_malformed_inputs_do_not_consume_attempts(client):
    browser, session = client
    user = create_user(session)
    record = add_code(session, user)

    assert reset(browser, code="12345").status_code == 422
    assert reset(browser, code="12345a").status_code == 422
    assert reset(browser, password="short").status_code == 422
    assert forgot(browser, email="no-es-correo").status_code == 422

    session.refresh(record)
    assert record.attempts == 0


def test_origin_protection_applies_to_password_reset_endpoints(client):
    browser, _ = client
    bad_origin = {"Origin": "https://evil.example"}

    assert (
        browser.post(
            "/auth/forgot-password",
            json={"email": "ana@example.com"},
            headers=bad_origin,
        ).status_code
        == 403
    )
    assert (
        browser.post(
            "/auth/reset-password",
            json={"email": "ana@example.com", "code": CODE, "password": NEW_PASSWORD},
            headers=bad_origin,
        ).status_code
        == 403
    )
