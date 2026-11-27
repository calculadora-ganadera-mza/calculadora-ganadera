import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import EmailSender
from app.models import EmailVerificationCode, User
from app.services.auth import token_hash


class EmailAlreadyVerifiedError(ValueError):
    """El correo del usuario ya está verificado."""


class InvalidVerificationCodeError(ValueError):
    """El código no coincide, venció o se le agotaron los intentos."""


class TooManyCodesError(ValueError):
    """Se pidió un código antes de la espera o por encima del máximo por hora."""


def send_verification_code(sender: EmailSender, to: str, code: str) -> None:
    """Manda el código por correo.

    Corre en segundo plano, cuando la sesión de la base ya se cerró: por eso
    recibe solo textos y no el usuario ni la sesión.
    """
    sender.send(
        to,
        "Código para verificar el correo",
        f"El código para verificar el correo es {code}.\n\n"
        f"Vence en {settings.verification_code_minutes} minutos. Si no se creó "
        "una cuenta con este correo, se puede ignorar este mensaje.",
    )


class EmailVerificationService:
    """Reglas del código de verificación.

    No hace commit: lo hace la operación que lo usa, que sabe cuándo terminó.
    """

    def __init__(self, session: Session):
        self.session = session

    def create_code(self, user: User) -> str:
        """Agrega un código nuevo y lo devuelve sin cifrar, para mandarlo.

        Deja sin efecto al anterior, porque solo vale el último.
        """
        code = f"{secrets.randbelow(10**6):06d}"
        self.session.add(
            EmailVerificationCode(
                user_id=user.id,
                code_hash=token_hash(code),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.verification_code_minutes),
            )
        )
        return code

    def resend(self, user: User) -> str:
        """Genera otro código si se respetan la espera y el máximo por hora."""
        self.lock_unverified(user)
        wait = settings.verification_code_resend_seconds
        per_hour = settings.verification_codes_per_hour
        if self.codes_since(user, timedelta(seconds=wait)):
            raise TooManyCodesError(
                f"Ya se envió un código hace menos de {wait} segundos."
            )
        if self.codes_since(user, timedelta(hours=1)) >= per_hour:
            raise TooManyCodesError("Se llegó al máximo de códigos por hora.")
        return self.create_code(user)

    def verify(self, user: User, code: str) -> None:
        """Verifica el correo si el código es el último y sigue vigente.

        Si el código no coincide, suma el intento antes de lanzar el error: quien
        llama tiene que hacer commit también en ese caso para no perderlo.
        """
        self.lock_unverified(user)
        latest = self.session.scalar(
            select(EmailVerificationCode)
            .where(EmailVerificationCode.user_id == user.id)
            .order_by(EmailVerificationCode.id.desc())
            .limit(1)
        )
        if latest is None or latest.expires_at <= datetime.now(UTC):
            raise InvalidVerificationCodeError(
                "No hay un código vigente. Hay que pedir uno nuevo."
            )
        if latest.attempts >= settings.verification_code_max_attempts:
            raise InvalidVerificationCodeError(
                "Se agotaron los intentos. Hay que pedir un código nuevo."
            )
        if not secrets.compare_digest(latest.code_hash, token_hash(code)):
            latest.attempts += 1
            raise InvalidVerificationCodeError("El código no es correcto.")
        user.email_verified = True

    def lock_unverified(self, user: User) -> None:
        """Bloquea el usuario y corta si el correo ya está verificado.

        Con el bloqueo, dos pedidos a la vez del mismo usuario se atienden de a
        uno y no pueden pasarse del máximo de intentos ni de códigos.
        """
        self.session.refresh(user, with_for_update=True)
        if user.email_verified:
            raise EmailAlreadyVerifiedError("El correo ya está verificado.")

    def codes_since(self, user: User, period: timedelta) -> int:
        """Códigos del usuario creados en el último período.

        Compara con el reloj de la base, que es el mismo que guarda created_at.
        """
        return self.session.execute(
            select(func.count())
            .select_from(EmailVerificationCode)
            .where(
                EmailVerificationCode.user_id == user.id,
                EmailVerificationCode.created_at > func.now() - period,
            )
        ).scalar_one()
