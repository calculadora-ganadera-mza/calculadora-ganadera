from datetime import datetime

from sqlalchemy import ForeignKey, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk


class PasswordResetCode(Base):
    """Código para recuperar la contraseña. Solo vale el último de cada usuario."""

    __tablename__ = "password_reset_code"

    id: Mapped[IntPk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    # No es único: dos códigos de seis dígitos pueden coincidir.
    code_hash: Mapped[str]
    expires_at: Mapped[datetime]
    attempts: Mapped[int] = mapped_column(server_default="0")
    # Impide reusar el código sin borrar la fila que cuenta para el límite por hora.
    used: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[CreatedAt]
