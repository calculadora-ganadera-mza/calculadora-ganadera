from typing import Any

from sqlalchemy import ForeignKeyConstraint, Index, false, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, IntPk
from app.models.enums import CalculationKind, pg_enum


class CarryingCapacityCalculation(Base):
    __tablename__ = "carrying_capacity_calculation"
    __table_args__ = (
        # Un solo resultado de campaña por sector y campaña
        Index(
            "uq_carrying_capacity_result_per_unit_season",
            "production_unit_id",
            "season_id",
            unique=True,
            postgresql_where=text("kind = 'result'"),
        ),
        Index(
            "ix_carrying_capacity_calculation_unit_created",
            "production_unit_id",
            "created_at",
        ),
        Index(
            "ix_carrying_capacity_calculation_scenario_created",
            "scenario_id",
            "created_at",
        ),
        ForeignKeyConstraint(
            ["season_id", "scenario_id"],
            ["season.id", "season.scenario_id"],
            name="fk_carrying_capacity_calc_season",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["production_unit_id", "scenario_id"],
            ["production_unit.id", "production_unit.scenario_id"],
            name="fk_carrying_capacity_calc_unit",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[IntPk]
    scenario_id: Mapped[int]
    season_id: Mapped[int] = mapped_column(index=True)
    production_unit_id: Mapped[int]
    kind: Mapped[CalculationKind] = mapped_column(
        pg_enum(CalculationKind, "calculation_kind")
    )
    season_updated: Mapped[bool] = mapped_column(server_default=false())
    input: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reference_values: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[CreatedAt]
