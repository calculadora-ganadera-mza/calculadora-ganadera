from sqlalchemy import false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPk


class Parameter(Base):
    __tablename__ = "parameter"

    id: Mapped[IntPk]
    key: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    value: Mapped[float]
    unit: Mapped[str]
    confirmed: Mapped[bool] = mapped_column(server_default=false())
    producer_editable: Mapped[bool] = mapped_column(server_default=false())
