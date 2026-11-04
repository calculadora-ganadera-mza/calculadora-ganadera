from sqlalchemy import CheckConstraint
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
