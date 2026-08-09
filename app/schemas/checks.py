from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CheckSummary(BaseModel):
    id: int
    title: str
    time_limit_seconds: int
    status: str
    started_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CheckDetail(CheckSummary):
    vocabulary_list_id: int
    total_words: int


class StudentResult(BaseModel):
    attempt_id: int
    user_id: int
    telegram_user_id: int
    display_name: str
    score: int
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    expired_answers: int
    percentage: float
    words_to_review: list[str]


class CheckResults(BaseModel):
    check_id: int
    title: str
    students: int
    average_score: float
    top_results: list[StudentResult]
