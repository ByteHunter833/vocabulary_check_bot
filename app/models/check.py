from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CheckStatus


class Check(Base, TimestampMixin):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    vocabulary_list_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vocabulary_list = relationship("VocabularyList", back_populates="checks")
    attempts = relationship("CheckAttempt", back_populates="check")


class CheckAttempt(Base):
    __tablename__ = "check_attempts"
    __table_args__ = (UniqueConstraint("check_id", "user_id", name="uq_check_attempt_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    check_id: Mapped[int] = mapped_column(
        ForeignKey("checks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expired_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    check = relationship("Check", back_populates="attempts")
    user = relationship("User", back_populates="attempts")
    questions = relationship(
        "QuestionAttempt",
        back_populates="check_attempt",
        cascade="all, delete-orphan",
        order_by="QuestionAttempt.question_number",
    )


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    __table_args__ = (
        UniqueConstraint(
            "check_attempt_id",
            "question_number",
            name="uq_question_attempt_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    check_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("check_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vocabulary_item_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_answer: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    check_attempt = relationship("CheckAttempt", back_populates="questions")
    vocabulary_item = relationship("VocabularyItem", back_populates="question_attempts")
