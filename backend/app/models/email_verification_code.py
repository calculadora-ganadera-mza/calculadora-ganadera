from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk


class EmailVerificationCode(Base):
    """Código para verificar el correo. Solo vale el último de cada usuario."""

    __tablename__ = "email_verification_code"

    id: Mapped[IntPk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    # No es único: dos códigos de seis dígitos pueden coincidir.
    code_hash: Mapped[str]
    expires_at: Mapped[datetime]
    attempts: Mapped[int] = mapped_column(server_default="0")
    created_at: Mapped[CreatedAt]
