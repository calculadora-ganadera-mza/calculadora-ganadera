"""add season start month

Revision ID: 5422e82f7f38
Revises: 8662234cefcf
Create Date: 2026-11-05 21:16:38.405368

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5422e82f7f38"
down_revision: str | Sequence[str] | None = "8662234cefcf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tabla mínima para insertar. No se importa el modelo: puede cambiar más
# adelante y esta migración tiene que seguir corriendo igual.
parameter = sa.table(
    "parameter",
    sa.column("key", sa.String),
    sa.column("description", sa.String),
    sa.column("value", sa.Double),
    sa.column("unit", sa.String),
    sa.column("confirmed", sa.Boolean),
    sa.column("producer_editable", sa.Boolean),
)

KEY = "season_start_month"


def upgrade() -> None:
    op.bulk_insert(
        parameter,
        [
            {
                "key": KEY,
                "description": "Mes de inicio de la campaña (1 = enero)",
                "value": 7,
                "unit": "mes",
                "confirmed": True,
                "producer_editable": False,
            }
        ],
    )


def downgrade() -> None:
    op.execute(parameter.delete().where(parameter.c.key == KEY))
