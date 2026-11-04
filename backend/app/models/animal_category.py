from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPk


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
