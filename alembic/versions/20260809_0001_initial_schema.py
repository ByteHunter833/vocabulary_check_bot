"""initial schema

Revision ID: 20260809_0001
Revises:
Create Date: 2026-08-09 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260809_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("ADMIN", "STUDENT", name="userrole", create_type=False)
    vocabulary_status_enum = postgresql.ENUM(
        "DRAFT",
        "PUBLISHED",
        "CANCELLED",
        name="vocabularystatus",
        create_type=False,
    )
    check_status_enum = postgresql.ENUM(
        "DRAFT",
        "PUBLISHED",
        "FINISHED",
        "CANCELLED",
        name="checkstatus",
        create_type=False,
    )

    role_enum.create(op.get_bind(), checkfirst=True)
    vocabulary_status_enum.create(op.get_bind(), checkfirst=True)
    check_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("role", role_enum, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
    )
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "vocabulary_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", vocabulary_status_enum, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_vocabulary_lists_created_by", "vocabulary_lists", ["created_by"])
    op.create_index("ix_vocabulary_lists_status", "vocabulary_lists", ["status"])

    op.create_table(
        "vocabulary_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "vocabulary_list_id",
            sa.Integer(),
            sa.ForeignKey("vocabulary_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("word", sa.String(length=255), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("accepted_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_vocabulary_items_list_position", "vocabulary_items", ["vocabulary_list_id", "position"]
    )

    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "vocabulary_list_id",
            sa.Integer(),
            sa.ForeignKey("vocabulary_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=False),
        sa.Column("status", check_status_enum, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_checks_status", "checks", ["status"])
    op.create_index("ix_checks_vocabulary_list_id", "checks", ["vocabulary_list_id"])

    op.create_table(
        "check_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "check_id", sa.Integer(), sa.ForeignKey("checks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expired_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("percentage", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("check_id", "user_id", name="uq_check_attempt_user"),
    )
    op.create_index("ix_check_attempts_check_id", "check_attempts", ["check_id"])
    op.create_index("ix_check_attempts_user_id", "check_attempts", ["user_id"])

    op.create_table(
        "question_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "check_attempt_id",
            sa.Integer(),
            sa.ForeignKey("check_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vocabulary_item_id",
            sa.Integer(),
            sa.ForeignKey("vocabulary_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("is_expired", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_question_attempts_attempt_number",
        "question_attempts",
        ["check_attempt_id", "question_number"],
    )
    op.create_index("ix_question_attempts_deadline", "question_attempts", ["deadline"])


def downgrade() -> None:
    op.drop_index("ix_question_attempts_deadline", table_name="question_attempts")
    op.drop_index("ix_question_attempts_attempt_number", table_name="question_attempts")
    op.drop_table("question_attempts")
    op.drop_index("ix_check_attempts_user_id", table_name="check_attempts")
    op.drop_index("ix_check_attempts_check_id", table_name="check_attempts")
    op.drop_table("check_attempts")
    op.drop_index("ix_checks_vocabulary_list_id", table_name="checks")
    op.drop_index("ix_checks_status", table_name="checks")
    op.drop_table("checks")
    op.drop_index("ix_vocabulary_items_list_position", table_name="vocabulary_items")
    op.drop_table("vocabulary_items")
    op.drop_index("ix_vocabulary_lists_status", table_name="vocabulary_lists")
    op.drop_index("ix_vocabulary_lists_created_by", table_name="vocabulary_lists")
    op.drop_table("vocabulary_lists")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")

    postgresql.ENUM(name="checkstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="vocabularystatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="userrole").drop(op.get_bind(), checkfirst=True)
