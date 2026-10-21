from sqlalchemy import false, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk
from app.models.enums import Role, pg_enum


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[IntPk]
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[Role] = mapped_column(
        pg_enum(Role, "role"), server_default=Role.PRODUCER.value
    )
    email_verified: Mapped[bool] = mapped_column(server_default=false())
    is_active: Mapped[bool] = mapped_column(server_default=true())
    created_at: Mapped[CreatedAt]
