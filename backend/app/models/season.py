from datetime import date

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk, UpdatedAt
from app.models.enums import RangeCondition, pg_enum


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


class HerdSeason(Base):
    __tablename__ = "herd_season"
    __table_args__ = (
        UniqueConstraint("season_id", "production_unit_id"),
        ForeignKeyConstraint(
            ["season_id", "scenario_id"],
            ["season.id", "season.scenario_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["production_unit_id", "scenario_id"],
            ["production_unit.id", "production_unit.scenario_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(breeding_start IS NULL) = (breeding_end IS NULL)",
            name="breeding_both_or_none",
        ),
        CheckConstraint(
            "breeding_end > breeding_start", name="breeding_end_after_start"
        ),
        CheckConstraint(
            "replacement_rate BETWEEN 0 AND 1", name="replacement_rate_range"
        ),
        CheckConstraint("weaning_rate BETWEEN 0 AND 1", name="weaning_rate_range"),
        CheckConstraint(
            "calving_body_condition BETWEEN 1 AND 5",
            name="calving_body_condition_range",
        ),
    )

    id: Mapped[IntPk]
    scenario_id: Mapped[int]
    season_id: Mapped[int]
    production_unit_id: Mapped[int] = mapped_column(index=True)
    breeding_start: Mapped[date | None]
    breeding_end: Mapped[date | None]
    range_condition: Mapped[RangeCondition] = mapped_column(
        pg_enum(RangeCondition, "range_condition")
    )
    replacement_rate: Mapped[float | None]
    weaning_rate: Mapped[float | None]
    calving_body_condition: Mapped[float | None]
    updated_at: Mapped[UpdatedAt]


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
