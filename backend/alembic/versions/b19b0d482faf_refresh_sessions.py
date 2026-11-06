"""Add rotating refresh sessions."""

import sqlalchemy as sa
from alembic import op

revision = "b19b0d482faf"
down_revision = "8662234cefcf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_session",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("family_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_refresh_session_user_id", "refresh_session", ["user_id"])
    op.create_index("ix_refresh_session_family_id", "refresh_session", ["family_id"])


def downgrade() -> None:
    op.drop_table("refresh_session")
