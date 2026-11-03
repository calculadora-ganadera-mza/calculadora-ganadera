from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import CheckConstraint, Computed, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk
from app.models.enums import ProductionSystem, pg_enum


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
