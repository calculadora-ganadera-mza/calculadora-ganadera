"""drop zone

Revision ID: 8662234cefcf
Revises: 07340f0fc2e6
Create Date: 2026-11-05 00:10:07.845646

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8662234cefcf"
down_revision: str | Sequence[str] | None = "07340f0fc2e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Copia de las subzonas de la migración de datos iniciales, para poder
# deshacer esta migración. No se importa: cada migración se sostiene sola.
ZONES = [
    {"name": "Subzona A", "mean_rainfall_mm": 408, "reliable_rainfall_mm": 315},
    {"name": "Subzona B", "mean_rainfall_mm": 350, "reliable_rainfall_mm": 255},
    {"name": "Subzona C", "mean_rainfall_mm": 275, "reliable_rainfall_mm": 185},
    {"name": "Subzona D", "mean_rainfall_mm": 225, "reliable_rainfall_mm": 150},
    {"name": "Subzona E", "mean_rainfall_mm": 175, "reliable_rainfall_mm": 110},
    {"name": "Subzona F", "mean_rainfall_mm": 135, "reliable_rainfall_mm": 78},
]


def upgrade() -> None:
    # Al borrar la columna, Postgres borra también su índice y su clave foránea.
    op.drop_column("scenario", "zone_id")
    op.drop_table("zone")


def downgrade() -> None:
    zone = op.create_table(
        "zone",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("mean_rainfall_mm", sa.Double(), nullable=False),
        sa.Column("reliable_rainfall_mm", sa.Double(), nullable=False),
        sa.CheckConstraint(
            "reliable_rainfall_mm <= mean_rainfall_mm",
            name=op.f("ck_zone_reliable_not_above_mean"),
        ),
        sa.CheckConstraint(
            "reliable_rainfall_mm > 0", name=op.f("ck_zone_reliable_rainfall_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zone")),
        sa.UniqueConstraint("name", name=op.f("uq_zone_name")),
    )
    op.bulk_insert(zone, ZONES)
    # Vuelve como opcional: puede haber escenarios creados sin subzona.
    op.add_column("scenario", sa.Column("zone_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_scenario_zone_id_zone"), "scenario", "zone", ["zone_id"], ["id"]
    )
    op.create_index(op.f("ix_scenario_zone_id"), "scenario", ["zone_id"])
