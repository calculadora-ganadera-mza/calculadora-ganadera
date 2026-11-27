"""add carrying capacity calculation

Revision ID: 7f4a2e9c1b08
Revises: d31d050c6bd5
Create Date: 2026-11-26 16:35:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7f4a2e9c1b08"
down_revision: str | Sequence[str] | None = "d31d050c6bd5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

calculation_kind = postgresql.ENUM(
    "result", "simulation", name="calculation_kind", create_type=False
)


def upgrade() -> None:
    calculation_kind.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "carrying_capacity_calculation",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("production_unit_id", sa.Integer(), nullable=False),
        sa.Column("kind", calculation_kind, nullable=False),
        sa.Column(
            "season_updated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("input", postgresql.JSONB(), nullable=False),
        sa.Column("reference_values", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["season_id", "scenario_id"],
            ["season.id", "season.scenario_id"],
            name="fk_carrying_capacity_calc_season",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["production_unit_id", "scenario_id"],
            ["production_unit.id", "production_unit.scenario_id"],
            name="fk_carrying_capacity_calc_unit",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_carrying_capacity_calculation"),
    )
    op.create_index(
        "ix_carrying_capacity_calculation_season_id",
        "carrying_capacity_calculation",
        ["season_id"],
    )
    op.create_index(
        "ix_carrying_capacity_calculation_unit_created",
        "carrying_capacity_calculation",
        ["production_unit_id", "created_at"],
    )
    op.create_index(
        "ix_carrying_capacity_calculation_scenario_created",
        "carrying_capacity_calculation",
        ["scenario_id", "created_at"],
    )
    op.create_index(
        "uq_carrying_capacity_result_per_unit_season",
        "carrying_capacity_calculation",
        ["production_unit_id", "season_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'result'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_carrying_capacity_result_per_unit_season",
        table_name="carrying_capacity_calculation",
    )
    op.drop_index(
        "ix_carrying_capacity_calculation_scenario_created",
        table_name="carrying_capacity_calculation",
    )
    op.drop_index(
        "ix_carrying_capacity_calculation_unit_created",
        table_name="carrying_capacity_calculation",
    )
    op.drop_index(
        "ix_carrying_capacity_calculation_season_id",
        table_name="carrying_capacity_calculation",
    )
    op.drop_table("carrying_capacity_calculation")
    calculation_kind.drop(op.get_bind(), checkfirst=True)
