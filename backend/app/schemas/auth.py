from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: int | None = None


class EmailVerificationInput(BaseModel):
    """Código de seis dígitos que llegó por correo."""

    code: str = Field(pattern=r"^[0-9]{6}$")
