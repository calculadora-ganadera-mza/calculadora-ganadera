"""rename animal categories

Revision ID: bd1f4a8c203e
Revises: 8e26e3041f57
Create Date: 2026-11-20 00:08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bd1f4a8c203e"
down_revision: str | Sequence[str] | None = "8e26e3041f57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

animal_category = sa.table(
    "animal_category",
    sa.column("code", sa.String),
    sa.column("name", sa.String),
)


def rename_categories(names: dict[str, str]) -> None:
    for code, name in names.items():
        op.execute(
            animal_category.update()
            .where(animal_category.c.code == op.inline_literal(code))
            .values(name=op.inline_literal(name))
        )


def upgrade() -> None:
    rename_categories({"cow": "Vaca", "heifer": "Vaquillona"})


def downgrade() -> None:
    rename_categories({"cow": "Vaca con cría", "heifer": "Vaquillona de recría"})
