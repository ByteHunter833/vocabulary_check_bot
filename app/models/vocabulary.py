from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import VocabularyStatus


class VocabularyList(Base, TimestampMixin):
    __tablename__ = "vocabulary_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[VocabularyStatus] = mapped_column(
        Enum(VocabularyStatus), default=VocabularyStatus.DRAFT, nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creator = relationship("User", back_populates="vocabulary_lists")
    items = relationship(
        "VocabularyItem",
        back_populates="vocabulary_list",
        cascade="all, delete-orphan",
        order_by="VocabularyItem.position",
    )
    checks = relationship("Check", back_populates="vocabulary_list")


class VocabularyItem(Base, TimestampMixin):
    __tablename__ = "vocabulary_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    vocabulary_list_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_answers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    vocabulary_list = relationship("VocabularyList", back_populates="items")
    question_attempts = relationship("QuestionAttempt", back_populates="vocabulary_item")
