from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import CheckConstraint, ForeignKey, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk


class WaterPoint(Base):
    __tablename__ = "water_point"
    __table_args__ = (CheckConstraint("refill_l_day > 0", name="refill_positive"),)

    id: Mapped[IntPk]
    production_unit_id: Mapped[int] = mapped_column(
        ForeignKey("production_unit.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]
    location: Mapped[WKBElement] = mapped_column(Geometry("POINT", srid=4326))
    refill_l_day: Mapped[float | None]
    shared: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[CreatedAt]
