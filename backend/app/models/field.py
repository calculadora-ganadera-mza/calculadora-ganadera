from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import CheckConstraint, Computed, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk
from app.models.enums import ProductionSystem, pg_enum


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


class ProductionUnit(Base):
    __tablename__ = "production_unit"
    __table_args__ = (
        CheckConstraint("ST_IsValid(polygon)", name="polygon_valid"),
        UniqueConstraint("id", "scenario_id"),
    )

    id: Mapped[IntPk]
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenario.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]
    production_system: Mapped[ProductionSystem] = mapped_column(
        pg_enum(ProductionSystem, "production_system")
    )
    polygon: Mapped[WKBElement] = mapped_column(Geometry("POLYGON", srid=4326))
    area_ha: Mapped[float] = mapped_column(
        Computed("ST_Area(polygon::geography) / 10000", persisted=True)
    )
    created_at: Mapped[CreatedAt]


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
    created_at: Mapped[CreatedAt]
