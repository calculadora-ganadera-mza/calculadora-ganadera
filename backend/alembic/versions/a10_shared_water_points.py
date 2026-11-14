"""Agrega confirmación de uso compartido de aguadas."""

import sqlalchemy as sa
from alembic import op

revision = "a10_shared_water_points"
down_revision = "f0ab01c44836"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "water_point",
        sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("water_point", "shared")
