"""add recommended herd parameters

Revision ID: e35137b81cfc
Revises: 9b3f2c1d7e4a
Create Date: 2026-11-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e35137b81cfc"
down_revision: str | Sequence[str] | None = "9b3f2c1d7e4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tabla mínima para insertar. No se importa el modelo para que la migración
# no cambie si el modelo cambia después.
parameter = sa.table(
    "parameter",
    sa.column("key", sa.String),
    sa.column("description", sa.String),
    sa.column("value", sa.Double),
    sa.column("unit", sa.String),
    sa.column("producer_editable", sa.Boolean),
)

PARAMETERS = [
    {
        "key": "weaned_calf_female_share",
        # Valor redondo: estudios de nacimientos de otros países dan entre 50 y
        # 53% de machos. No hay un dato medido en Mendoza.
        "description": "Parte de hembras entre los terneros destetados",
        "value": 0.5,
        "unit": "fracción",
    },
    {
        "key": "normal_weaning_age_months",
        "description": "Edad del ternero al destete normal",
        "value": 6,
        "unit": "meses",
    },
    {
        "key": "early_weaning_age_months",
        "description": "Edad del ternero al destete precoz",
        "value": 3,
        "unit": "meses",
    },
    {
        "key": "heifer_first_breeding_age_months",
        "description": "Edad de la vaquillona en su primer entore",
        "value": 24,
        "unit": "meses",
    },
]


def upgrade() -> None:
    op.bulk_insert(
        parameter, [{**row, "producer_editable": False} for row in PARAMETERS]
    )


def downgrade() -> None:
    op.execute(
        parameter.delete().where(
            parameter.c.key.in_([row["key"] for row in PARAMETERS])
        )
    )
