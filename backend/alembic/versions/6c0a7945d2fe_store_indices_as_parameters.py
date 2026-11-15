"""store indices as parameters

Revision ID: 6c0a7945d2fe
Revises: c10_merge_aguadas_rodeos
Create Date: 2026-11-15 14:26:55.773449

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c0a7945d2fe"
down_revision: str | Sequence[str] | None = "c10_merge_aguadas_rodeos"
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

# Los índices se cargan sin valor: el administrador los completa más adelante.
INDICES = [
    {
        "key": "range_condition_index_fair",
        "description": "Índice de receptividad para estado del campo regular",
    },
    {
        "key": "range_condition_index_good",
        "description": "Índice de receptividad para estado del campo bueno",
    },
    {
        "key": "range_condition_index_very_good",
        "description": "Índice de receptividad para estado del campo muy bueno",
    },
    {
        "key": "early_weaning_index",
        "description": "Índice de receptividad con destete precoz",
    },
    {
        "key": "supplementation_index",
        "description": "Índice de receptividad con suplementación",
    },
]


def upgrade() -> None:
    op.drop_column("parameter", "confirmed")
    op.alter_column("parameter", "value", nullable=True)
    op.bulk_insert(
        parameter,
        [
            {**index, "value": None, "unit": "índice", "producer_editable": False}
            for index in INDICES
        ],
    )


def downgrade() -> None:
    op.execute(
        parameter.delete().where(
            parameter.c.key.in_([index["key"] for index in INDICES])
        )
    )
    op.alter_column("parameter", "value", nullable=False)
    op.add_column(
        "parameter",
        sa.Column(
            "confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    # Antes de esta migración todos los parámetros estaban confirmados.
    op.execute("UPDATE parameter SET confirmed = true")
