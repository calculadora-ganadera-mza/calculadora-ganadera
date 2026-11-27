import re
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.models import EmailVerificationCode
from app.services.auth import token_hash

CODE = "123456"
OTHER_CODE = "654321"


def add_code(session, user, code=CODE, **fields) -> EmailVerificationCode:
    """Guarda un código conocido, vigente salvo que se indique otro vencimiento."""
    fields.setdefault("expires_at", datetime.now(UTC) + timedelta(minutes=15))
    record = EmailVerificationCode(
        user_id=user.id, code_hash=token_hash(code), **fields
    )
    session.add(record)
    session.flush()
    return record


def verify(api, code=CODE):
    return api.post("/auth/verify-email", json={"code": code})


def resend(api):
    return api.post("/auth/resend-verification")


def test_correct_code_verifies_email(api, session, user):
    add_code(session, user)

    assert verify(api).status_code == 204
    assert api.get("/auth/me").json()["email_verified"] is True
    # El código ya usado da 409: el correo quedó verificado.
    assert verify(api).status_code == 409


def test_wrong_code_counts_a_failed_attempt(api, session, user):
    record = add_code(session, user)

    assert verify(api, OTHER_CODE).status_code == 422
    # Descarta lo que la ruta no guardó, como al cerrarse la sesión del pedido.
    session.rollback()
    session.refresh(record)
    assert record.attempts == 1


def test_code_is_annulled_after_max_attempts(api, session, user):
    add_code(session, user)
    for _ in range(settings.verification_code_max_attempts):
        verify(api, OTHER_CODE)

    assert verify(api).status_code == 422


def test_last_failed_attempt_says_attempts_ran_out(api, session, user):
    add_code(session, user)
    for _ in range(settings.verification_code_max_attempts - 1):
        verify(api, OTHER_CODE)

    response = verify(api, OTHER_CODE)
    assert response.status_code == 422
    assert "agotaron" in response.json()["detail"]


def test_malformed_code_does_not_count_as_attempt(api, session, user):
    record = add_code(session, user)

    for code in ["12345", "1234567", "12345a"]:
        assert verify(api, code).status_code == 422
    session.refresh(record)
    assert record.attempts == 0


def test_expired_code_is_rejected(api, session, user):
    add_code(session, user, expires_at=datetime.now(UTC) - timedelta(seconds=1))

    assert verify(api).status_code == 422


def test_only_latest_code_counts(api, session, user):
    add_code(session, user)
    add_code(session, user, OTHER_CODE)

    assert verify(api).status_code == 422
    assert verify(api, OTHER_CODE).status_code == 204


def test_verify_without_code_is_rejected(api):
    assert verify(api).status_code == 422


def test_resend_mails_a_new_code(api, user, outbox):
    assert resend(api).status_code == 202

    [(to, _, text)] = outbox
    [code] = re.findall(r"\b\d{6}\b", text)
    assert to == user.email
    assert verify(api, code).status_code == 204


def test_resend_waits_after_last_code(api, session, user, outbox):
    add_code(session, user)

    assert resend(api).status_code == 429
    assert outbox == []


def test_resend_has_hourly_limit(api, session, user):
    # Ya pasó la espera entre pedidos, pero los códigos cuentan para la hora.
    two_minutes_ago = datetime.now(UTC) - timedelta(minutes=2)
    for _ in range(settings.verification_codes_per_hour):
        add_code(session, user, created_at=two_minutes_ago)

    assert resend(api).status_code == 429


def test_codes_older_than_an_hour_do_not_count(api, session, user):
    over_an_hour_ago = datetime.now(UTC) - timedelta(minutes=61)
    for _ in range(settings.verification_codes_per_hour):
        add_code(session, user, created_at=over_an_hour_ago)

    assert resend(api).status_code == 202


def test_verified_email_cannot_resend(api, session, user):
    user.email_verified = True
    session.flush()

    assert resend(api).status_code == 409
