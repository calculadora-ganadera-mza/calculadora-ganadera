from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk


class Scenario(Base):
    __tablename__ = "scenario"

    id: Mapped[IntPk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    zone_id: Mapped[int] = mapped_column(ForeignKey("zone.id"), index=True)
    name: Mapped[str]
    location: Mapped[WKBElement | None] = mapped_column(Geometry("POINT", srid=4326))
    created_at: Mapped[CreatedAt]
