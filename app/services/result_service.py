from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Check, CheckAttempt, QuestionAttempt, User
from app.schemas.checks import CheckResults, StudentResult


def display_name(user: User) -> str:
    full_name = " ".join(part for part in [user.display_name, user.patronymic] if part)
    if full_name:
        return full_name
    full_name = " ".join(part for part in [user.first_name, user.last_name] if part)
    return full_name or user.username or str(user.telegram_user_id)


class ResultService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_attempt_result(self, attempt_id: int) -> StudentResult:
        result = await self.session.execute(
            select(CheckAttempt)
            .where(CheckAttempt.id == attempt_id)
            .options(
                selectinload(CheckAttempt.user),
                selectinload(CheckAttempt.questions).selectinload(QuestionAttempt.vocabulary_item),
            )
        )
        attempt = result.scalar_one()
        return self._attempt_to_result(attempt)

    async def get_check_results(self, check_id: int) -> CheckResults:
        check_result = await self.session.execute(select(Check).where(Check.id == check_id))
        check = check_result.scalar_one()
        attempt_result = await self.session.execute(
            select(CheckAttempt)
            .where(CheckAttempt.check_id == check_id, CheckAttempt.finished_at.is_not(None))
            .options(
                selectinload(CheckAttempt.user),
                selectinload(CheckAttempt.questions).selectinload(QuestionAttempt.vocabulary_item),
            )
            .order_by(CheckAttempt.percentage.desc(), CheckAttempt.finished_at.asc())
        )
        attempts = list(attempt_result.scalars())
        top_results = [self._attempt_to_result(attempt) for attempt in attempts]
        average = (
            round(sum(attempt.percentage for attempt in attempts) / len(attempts), 2)
            if attempts
            else 0
        )
        return CheckResults(
            check_id=check.id,
            title=check.title,
            students=len(attempts),
            average_score=average,
            top_results=top_results,
        )

    async def get_user_results(self, user_id: int) -> list[StudentResult]:
        result = await self.session.execute(
            select(CheckAttempt)
            .where(CheckAttempt.user_id == user_id, CheckAttempt.finished_at.is_not(None))
            .options(
                selectinload(CheckAttempt.user),
                selectinload(CheckAttempt.questions).selectinload(QuestionAttempt.vocabulary_item),
            )
            .order_by(CheckAttempt.finished_at.desc())
        )
        return [self._attempt_to_result(attempt) for attempt in result.scalars()]

    def _attempt_to_result(self, attempt: CheckAttempt) -> StudentResult:
        words_to_review = [
            question.vocabulary_item.word
            for question in attempt.questions
            if question.is_expired or question.is_correct is False
        ]
        return StudentResult(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            telegram_user_id=attempt.user.telegram_user_id,
            display_name=display_name(attempt.user),
            score=attempt.score,
            total_questions=attempt.total_questions,
            correct_answers=attempt.correct_answers,
            incorrect_answers=attempt.incorrect_answers,
            expired_answers=attempt.expired_answers,
            percentage=attempt.percentage,
            words_to_review=words_to_review,
        )
