from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.user import UserEmail, UserPassword

VerificationCode = Annotated[str, Field(pattern=r"^[0-9]{6}$")]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: int | None = None


class EmailVerificationInput(BaseModel):
    """Código de seis dígitos que llegó por correo."""

    code: VerificationCode


class ForgotPasswordInput(BaseModel):
    """Correo para pedir el código de recuperación de contraseña."""

    email: UserEmail


class ResetPasswordInput(BaseModel):
    """Datos para cambiar la contraseña usando el código recibido por correo."""

    email: UserEmail
    code: VerificationCode
    password: UserPassword
