from sqlalchemy import CheckConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPk


class Zone(Base):
    __tablename__ = "zone"
    __table_args__ = (
        CheckConstraint("reliable_rainfall_mm > 0", name="reliable_rainfall_positive"),
        CheckConstraint(
            "reliable_rainfall_mm <= mean_rainfall_mm", name="reliable_not_above_mean"
        ),
    )

    id: Mapped[IntPk]
    name: Mapped[str] = mapped_column(unique=True)
    mean_rainfall_mm: Mapped[float]
    reliable_rainfall_mm: Mapped[float]


class Parameter(Base):
    __tablename__ = "parameter"

    id: Mapped[IntPk]
    key: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    value: Mapped[float]
    unit: Mapped[str]
    confirmed: Mapped[bool] = mapped_column(server_default=false())
    producer_editable: Mapped[bool] = mapped_column(server_default=false())


class AnimalCategory(Base):
    __tablename__ = "animal_category"
    __table_args__ = (
        CheckConstraint("cow_equivalent > 0", name="cow_equivalent_positive"),
        CheckConstraint("summer_water_l_day > 0", name="summer_water_positive"),
        CheckConstraint("winter_water_l_day > 0", name="winter_water_positive"),
    )

    id: Mapped[IntPk]
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(unique=True)
    cow_equivalent: Mapped[float]
    summer_water_l_day: Mapped[float]
    winter_water_l_day: Mapped[float]
