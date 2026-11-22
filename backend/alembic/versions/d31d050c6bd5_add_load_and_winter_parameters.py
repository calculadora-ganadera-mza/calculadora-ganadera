"""add load and winter parameters

Revision ID: d31d050c6bd5
Revises: bd1f4a8c203e
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d31d050c6bd5"
down_revision: str | Sequence[str] | None = "bd1f4a8c203e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

parameter = sa.table(
    "parameter",
    sa.column("key", sa.String),
    sa.column("description", sa.String),
    sa.column("value", sa.Double),
    sa.column("unit", sa.String),
    sa.column("producer_editable", sa.Boolean),
)

# Valores provisorios.
PARAMETERS = [
    {
        "key": "winter_start_month",
        "description": "Primer mes del invierno (1 = enero)",
        "value": 6,
        "unit": "mes",
    },
    {
        "key": "winter_end_month",
        "description": "Último mes del invierno (1 = enero)",
        "value": 8,
        "unit": "mes",
    },
    {
        "key": "load_thermometer_below_threshold",
        "description": "Fracción mínima para estar dentro de la capacidad",
        "value": 0.9,
        "unit": "fracción",
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
