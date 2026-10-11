"""question attempt constraints

Revision ID: 20260904_0003
Revises: 20260809_0002
Create Date: 2026-09-04 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20260904_0003"
down_revision = "20260809_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM question_attempts qa
        USING question_attempts duplicate
        WHERE qa.check_attempt_id = duplicate.check_attempt_id
          AND qa.question_number = duplicate.question_number
          AND qa.id > duplicate.id
        """
    )
    op.create_unique_constraint(
        "uq_question_attempt_number",
        "question_attempts",
        ["check_attempt_id", "question_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_question_attempt_number",
        "question_attempts",
        type_="unique",
    )
