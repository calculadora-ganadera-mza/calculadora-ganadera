"""add scenario is main

Revision ID: f0ab01c44836
Revises: 5422e82f7f38
Create Date: 2026-11-09 01:16:38.221873

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0ab01c44836"
down_revision: str | Sequence[str] | None = "5422e82f7f38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenario",
        sa.Column(
            "is_main", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    # Los establecimientos que ya existen: el primero de cada usuario es el principal
    op.execute(
        """
        UPDATE scenario SET is_main = true
        WHERE id IN (
            SELECT DISTINCT ON (user_id) id FROM scenario
            ORDER BY user_id, created_at, id
        )
        """
    )
    op.create_index(
        "uq_scenario_main_per_user",
        "scenario",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_main"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_scenario_main_per_user",
        table_name="scenario",
        postgresql_where=sa.text("is_main"),
    )
    op.drop_column("scenario", "is_main")
