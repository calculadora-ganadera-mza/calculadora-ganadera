"""check parameter value

Revision ID: 537d3939f712
Revises: 6c0a7945d2fe
Create Date: 2026-11-15 20:20:36.313064

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3f2c1d7e4a"
down_revision: str | Sequence[str] | None = "6c0a7945d2fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Todo valor cargado es mayor que 0. Solo los índices pueden quedar sin valor,
# hasta que el administrador los cargue. El IS NOT NULL hace falta porque un
# CHECK que da NULL no rechaza la fila.
CONDITION = (
    "(value IS NOT NULL AND value > 0) OR (value IS NULL AND key IN ("
    "'range_condition_index_fair', 'range_condition_index_good', "
    "'range_condition_index_very_good', 'early_weaning_index', "
    "'supplementation_index'))"
)


def upgrade() -> None:
    op.create_check_constraint(
        op.f("ck_parameter_value_positive"), "parameter", CONDITION
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_parameter_value_positive"), "parameter", type_="check")
