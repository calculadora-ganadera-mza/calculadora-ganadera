"""add herd early weaning and supplemented

Revision ID: b2d15f996148
Revises: f0ab01c44836
Create Date: 2026-11-13 20:38:09.980444

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2d15f996148"
down_revision: str | Sequence[str] | None = "f0ab01c44836"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Destete precoz y suplementación: casillas del rodeo, sin marcar por defecto
    for column in ("early_weaning", "supplemented"):
        op.add_column(
            "herd_season",
            sa.Column(
                column, sa.Boolean(), server_default=sa.text("false"), nullable=False
            ),
        )


def downgrade() -> None:
    op.drop_column("herd_season", "supplemented")
    op.drop_column("herd_season", "early_weaning")
