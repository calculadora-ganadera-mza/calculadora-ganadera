from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk, UpdatedAt


class Season(Base):
    __tablename__ = "season"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="end_after_start"),
        CheckConstraint("rainfall_mm >= 0", name="rainfall_non_negative"),
        ExcludeConstraint(
            ("scenario_id", "="),
            (text("daterange(start_date, end_date, '[]')"), "&&"),
            name="ex_season_no_overlap",
            using="gist",
        ),
        UniqueConstraint("id", "scenario_id"),
    )

    id: Mapped[IntPk]
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("scenario.id", ondelete="CASCADE"), index=True
    )
    start_date: Mapped[date]
    end_date: Mapped[date]
    rainfall_mm: Mapped[float | None]
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]
