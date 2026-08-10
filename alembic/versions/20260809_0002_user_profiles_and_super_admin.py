"""user profiles and super admin

Revision ID: 20260809_0002
Revises: 20260809_0001
Create Date: 2026-08-09 00:00:01.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260809_0002"
down_revision = "20260809_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPER_ADMIN' BEFORE 'ADMIN'")
    op.add_column("users", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("patronymic", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "registration_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        """
        UPDATE users
        SET registration_completed = true
        WHERE role = 'ADMIN'
        """
    )


def downgrade() -> None:
    op.drop_column("users", "registration_completed")
    op.drop_column("users", "patronymic")
    op.drop_column("users", "display_name")
