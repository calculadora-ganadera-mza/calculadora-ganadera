"""add water calendar parameters

Revision ID: 8e26e3041f57
Revises: e35137b81cfc
Create Date: 2026-11-18 21:39:14.641402

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8e26e3041f57"
down_revision: str | Sequence[str] | None = "e35137b81cfc"
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
        "key": "gestation_days",
        # Falta citar la fuente (#26).
        "description": "Días de gestación de la vaca",
        "value": 283,
        "unit": "días",
    },
    {
        "key": "summer_start_month",
        # Provisorio (#26).
        "description": "Primer mes del verano (1 = enero)",
        "value": 12,
        "unit": "mes",
    },
    {
        "key": "summer_end_month",
        # Provisorio (#26).
        "description": "Último mes del verano (1 = enero)",
        "value": 2,
        "unit": "mes",
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
