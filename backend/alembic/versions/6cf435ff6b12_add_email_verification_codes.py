"""add email verification codes

Revision ID: 6cf435ff6b12
Revises: 7f4a2e9c1b08
Create Date: 2026-11-26 23:11:37.954257

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6cf435ff6b12"
down_revision: str | Sequence[str] | None = "7f4a2e9c1b08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_verification_code",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_email_verification_code_user_id", "email_verification_code", ["user_id"]
    )


def downgrade() -> None:
    op.drop_table("email_verification_code")
