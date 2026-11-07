from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk


class RefreshSession(Base):
    __tablename__ = "refresh_session"

    id: Mapped[IntPk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(unique=True)
    family_id: Mapped[str] = mapped_column(index=True)
    expires_at: Mapped[datetime]
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[CreatedAt]
