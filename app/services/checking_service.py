from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Check,
    CheckAttempt,
    CheckStatus,
    QuestionAttempt,
    User,
    UserRole,
    VocabularyItem,
    VocabularyList,
    VocabularyStatus,
)
from app.services.answer_evaluator import AnswerEvaluator, RuleBasedEvaluator
from app.services.grading import calculate_percentage
from app.services.timer import is_answer_expired


class CheckFlowError(RuntimeError):
    pass


@dataclass(frozen=True)
class AnswerOutcome:
    question: QuestionAttempt
    is_correct: bool
    is_expired: bool
    finished: bool
    next_question: QuestionAttempt | None


class CheckingService:
    def __init__(
        self,
        session: AsyncSession,
        evaluator: AnswerEvaluator | None = None,
    ) -> None:
        self.session = session
        self.evaluator = evaluator or RuleBasedEvaluator()

    async def publish_check(
        self,
        *,
        vocabulary_list: VocabularyList,
        title: str | None = None,
        time_limit_seconds: int = 60,
    ) -> Check:
        if vocabulary_list.status == VocabularyStatus.CANCELLED:
            raise CheckFlowError("Cannot publish a cancelled vocabulary list.")

        vocabulary_list.status = VocabularyStatus.PUBLISHED
        vocabulary_list.published_at = datetime.now(UTC)
        check = Check(
            vocabulary_list_id=vocabulary_list.id,
            title=title or vocabulary_list.title,
            time_limit_seconds=time_limit_seconds,
            status=CheckStatus.PUBLISHED,
            started_at=datetime.now(UTC),
        )
        self.session.add(check)
        await self.session.commit()
        await self.session.refresh(check)
        return check

    async def get_check_with_items(self, check_id: int) -> Check:
        result = await self.session.execute(
            select(Check)
            .where(Check.id == check_id)
            .options(selectinload(Check.vocabulary_list).selectinload(VocabularyList.items))
        )
        check = result.scalar_one_or_none()
        if check is None:
            raise CheckFlowError("Check was not found.")
        return check

    async def start_attempt(self, *, check_id: int, user: User) -> CheckAttempt:
        check = await self.get_check_with_items(check_id)
        if check.status != CheckStatus.PUBLISHED:
            raise CheckFlowError("This check is not available.")

        result = await self.session.execute(
            select(CheckAttempt)
            .where(CheckAttempt.check_id == check_id, CheckAttempt.user_id == user.id)
            .options(selectinload(CheckAttempt.questions))
        )
        existing_attempt = result.scalar_one_or_none()
        if existing_attempt is not None:
            if existing_attempt.finished_at is not None:
                raise CheckFlowError("You already completed this check.")
            return existing_attempt

        items = list(check.vocabulary_list.items)
        if not items:
            raise CheckFlowError("This check has no vocabulary items.")

        attempt = CheckAttempt(
            check_id=check.id,
            user_id=user.id,
            total_questions=len(items),
        )
        self.session.add(attempt)
        await self.session.flush()
        await self._create_question_attempt(attempt, items[0], 1, check.time_limit_seconds)
        await self.session.commit()
        await self.session.refresh(attempt, attribute_names=["questions"])
        return attempt

    async def get_current_question(self, attempt_id: int) -> QuestionAttempt | None:
        result = await self.session.execute(
            select(QuestionAttempt)
            .where(
                QuestionAttempt.check_attempt_id == attempt_id,
                QuestionAttempt.answered_at.is_(None),
                QuestionAttempt.is_expired.is_(False),
            )
            .order_by(QuestionAttempt.question_number.desc())
            .options(selectinload(QuestionAttempt.vocabulary_item))
        )
        return result.scalars().first()

    async def get_active_attempt_for_user(self, user: User) -> CheckAttempt | None:
        result = await self.session.execute(
            select(CheckAttempt)
            .where(CheckAttempt.user_id == user.id, CheckAttempt.finished_at.is_(None))
            .options(selectinload(CheckAttempt.questions), selectinload(CheckAttempt.check))
            .order_by(CheckAttempt.started_at.desc())
        )
        return result.scalars().first()

    async def submit_answer(
        self,
        *,
        attempt_id: int,
        answer: str,
        answered_at: datetime | None = None,
    ) -> AnswerOutcome:
        answered_at = answered_at or datetime.now(UTC)
        question = await self._load_open_question(attempt_id)
        if question is None:
            raise CheckFlowError("There is no active question.")

        expired = is_answer_expired(answered_at, question.deadline)
        if expired:
            question.answered_at = answered_at
            question.user_answer = answer
            question.is_correct = False
            question.is_expired = True
        else:
            result = self.evaluator.evaluate(answer, question.vocabulary_item)
            question.answered_at = answered_at
            question.user_answer = answer
            question.is_correct = result.is_correct
            question.is_expired = False

        next_question = await self._advance_or_finish(question.check_attempt)
        await self.session.commit()
        return AnswerOutcome(
            question=question,
            is_correct=bool(question.is_correct),
            is_expired=question.is_expired,
            finished=next_question is None and question.check_attempt.finished_at is not None,
            next_question=next_question,
        )

    async def expire_current_question(
        self,
        *,
        attempt_id: int,
        now: datetime | None = None,
    ) -> AnswerOutcome | None:
        now = now or datetime.now(UTC)
        question = await self._load_open_question(attempt_id)
        if question is None or now <= question.deadline:
            return None

        question.answered_at = now
        question.user_answer = None
        question.is_correct = False
        question.is_expired = True
        next_question = await self._advance_or_finish(question.check_attempt)
        await self.session.commit()
        return AnswerOutcome(
            question=question,
            is_correct=False,
            is_expired=True,
            finished=next_question is None and question.check_attempt.finished_at is not None,
            next_question=next_question,
        )

    async def _load_open_question(self, attempt_id: int) -> QuestionAttempt | None:
        result = await self.session.execute(
            select(QuestionAttempt)
            .where(
                QuestionAttempt.check_attempt_id == attempt_id,
                QuestionAttempt.answered_at.is_(None),
                QuestionAttempt.is_expired.is_(False),
            )
            .order_by(QuestionAttempt.question_number.desc())
            .options(
                selectinload(QuestionAttempt.vocabulary_item),
                selectinload(QuestionAttempt.check_attempt)
                .selectinload(CheckAttempt.check)
                .selectinload(Check.vocabulary_list)
                .selectinload(VocabularyList.items),
                selectinload(QuestionAttempt.check_attempt).selectinload(CheckAttempt.questions),
            )
        )
        return result.scalars().first()

    async def _advance_or_finish(self, attempt: CheckAttempt) -> QuestionAttempt | None:
        check = attempt.check
        answered_numbers = {question.question_number for question in attempt.questions}
        next_number = max(answered_numbers, default=0) + 1
        items = list(check.vocabulary_list.items)

        if next_number <= len(items):
            return await self._create_question_attempt(
                attempt,
                items[next_number - 1],
                next_number,
                check.time_limit_seconds,
            )

        await self._finish_attempt(attempt)
        return None

    async def _create_question_attempt(
        self,
        attempt: CheckAttempt,
        item: VocabularyItem,
        question_number: int,
        time_limit_seconds: int,
    ) -> QuestionAttempt:
        started_at = datetime.now(UTC)
        question = QuestionAttempt(
            check_attempt_id=attempt.id,
            vocabulary_item_id=item.id,
            vocabulary_item=item,
            question_number=question_number,
            started_at=started_at,
            deadline=started_at + timedelta(seconds=time_limit_seconds),
        )
        self.session.add(question)
        await self.session.flush()
        return question

    async def _finish_attempt(self, attempt: CheckAttempt) -> None:
        result = await self.session.execute(
            select(QuestionAttempt).where(QuestionAttempt.check_attempt_id == attempt.id)
        )
        questions = list(result.scalars())
        correct = sum(
            1 for question in questions if question.is_correct is True and not question.is_expired
        )
        expired = sum(1 for question in questions if question.is_expired)
        incorrect = sum(
            1
            for question in questions
            if question.answered_at is not None
            and question.is_correct is False
            and not question.is_expired
        )
        total = attempt.total_questions or len(questions)
        attempt.score = correct
        attempt.total_questions = total
        attempt.correct_answers = correct
        attempt.incorrect_answers = incorrect
        attempt.expired_answers = expired
        attempt.percentage = calculate_percentage(correct, total)
        attempt.finished_at = datetime.now(UTC)

    async def list_published_checks(self) -> list[Check]:
        result = await self.session.execute(
            select(Check)
            .where(Check.status == CheckStatus.PUBLISHED)
            .order_by(Check.started_at.desc().nullslast(), Check.created_at.desc())
        )
        return list(result.scalars())

    async def count_students(self) -> int:
        result = await self.session.execute(
            select(func.count(User.id)).where(User.role == UserRole.STUDENT)
        )
        return int(result.scalar_one())
