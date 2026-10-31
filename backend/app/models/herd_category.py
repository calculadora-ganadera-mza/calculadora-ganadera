from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IntPk


class HerdCategory(Base):
    __tablename__ = "herd_category"
    __table_args__ = (
        UniqueConstraint("herd_season_id", "animal_category_id"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    )

    id: Mapped[IntPk]
    herd_season_id: Mapped[int] = mapped_column(
        ForeignKey("herd_season.id", ondelete="CASCADE")
    )
    animal_category_id: Mapped[int] = mapped_column(
        ForeignKey("animal_category.id"), index=True
    )
    quantity: Mapped[int]
