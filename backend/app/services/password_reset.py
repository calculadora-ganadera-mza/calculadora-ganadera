import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import EmailSender
from app.core.password import hash_password
from app.models import PasswordResetCode, User
from app.services.auth import AuthService, token_hash

INVALID_RESET_CODE_MESSAGE = (
    "El código no es válido. Hay que revisarlo o pedir uno nuevo."
)


class InvalidPasswordResetCodeError(ValueError):
    """El código no coincide, venció, ya fue usado o se le agotaron los intentos."""


def send_password_reset_code(sender: EmailSender, to: str, code: str) -> None:
    """Manda el código de recuperación por correo.

    Corre en segundo plano, cuando la sesión de la base ya se cerró: por eso
    recibe solo textos y no el usuario ni la sesión.
    """
    sender.send(
        to,
        "Código para recuperar la contraseña",
        f"El código para cambiar la contraseña es {code}.\n\n"
        f"Vence en {settings.password_reset_code_minutes} minutos. Si no se pidió "
        "recuperar la contraseña, se puede ignorar este mensaje.",
    )


class PasswordResetService:
    """Reglas del código de recuperación de contraseña.

    No hace commit: lo hace la operación que lo usa, que sabe cuándo terminó.
    """

    def __init__(self, session: Session):
        self.session = session

    def request_code(self, email: str) -> tuple[str, str] | None:
        """Genera un código nuevo si existe la cuenta y se respetan los límites.

        Devuelve `(correo, código)` para enviarlo en segundo plano, o `None` si no
        corresponde enviar nada, sin revelar qué ocurrió.
        """
        normalized = email.lower()
        code = f"{secrets.randbelow(10**6):06d}"
        hashed = token_hash(code)

        user = self.session.scalar(
            select(User).where(User.email == normalized).with_for_update()
        )
        if user is None:
            return None

        wait = settings.password_reset_code_resend_seconds
        per_hour = settings.password_reset_codes_per_hour
        if self.codes_since(user, timedelta(seconds=wait)):
            return None
        if self.codes_since(user, timedelta(hours=1)) >= per_hour:
            return None

        self.session.add(
            PasswordResetCode(
                user_id=user.id,
                code_hash=hashed,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.password_reset_code_minutes),
            )
        )
        return user.email, code

    def reset_password(self, email: str, code: str, new_password: str) -> None:
        """Cambia la contraseña si el código es el último y sigue vigente.

        Si el código no coincide, suma el intento antes de lanzar el error: quien
        llama tiene que hacer commit también en ese caso para no perderlo.
        """
        normalized = email.lower()
        user = self.session.scalar(
            select(User).where(User.email == normalized).with_for_update()
        )
        if user is None:
            raise InvalidPasswordResetCodeError(INVALID_RESET_CODE_MESSAGE)

        latest_code = self.session.scalar(
            select(PasswordResetCode)
            .where(PasswordResetCode.user_id == user.id)
            .order_by(PasswordResetCode.id.desc())
            .limit(1)
        )
        if (
            latest_code is None
            or latest_code.used
            or latest_code.expires_at <= datetime.now(UTC)
            or latest_code.attempts >= settings.password_reset_code_max_attempts
        ):
            raise InvalidPasswordResetCodeError(INVALID_RESET_CODE_MESSAGE)

        if not secrets.compare_digest(latest_code.code_hash, token_hash(code)):
            latest_code.attempts += 1
            raise InvalidPasswordResetCodeError(INVALID_RESET_CODE_MESSAGE)

        latest_code.used = True
        user.password_hash = hash_password(new_password)
        user.email_verified = True
        AuthService(self.session).revoke_all_for_user(user.id)

    def codes_since(self, user: User, period: timedelta) -> int:
        """Códigos de recuperación del usuario creados en el último período.

        Compara con el reloj de la base, que es el mismo que guarda created_at.
        """
        return self.session.execute(
            select(func.count())
            .select_from(PasswordResetCode)
            .where(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.created_at > func.now() - period,
            )
        ).scalar_one()
