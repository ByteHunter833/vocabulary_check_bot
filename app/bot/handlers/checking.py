from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.bot.keyboards.checking import start_check_keyboard
from app.bot.utils import format_student_result
from app.core.database import async_session_factory
from app.models import QuestionAttempt
from app.services.checking_service import CheckFlowError, CheckingService
from app.services.result_service import ResultService
from app.services.user_service import TelegramUserData, UserService

router = Router()
logger = get_logger(__name__)


async def _upsert_user(message_or_callback, session: AsyncSession):
    from_user = message_or_callback.from_user
    return await UserService(session).upsert_telegram_user(
        TelegramUserData(
            id=from_user.id,
            username=from_user.username,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
        )
    )


@router.message(Command("checks"))
async def list_checks(message: Message, session: AsyncSession) -> None:
    await _upsert_user(message, session)
    checks = await CheckingService(session).list_published_checks()
    if not checks:
        await message.answer("No active vocabulary checks are available right now.")
        return
    for check in checks[:10]:
        await message.answer(
            "Vocabulary Check\n\n"
            f"{check.title}\n\n"
            f"Time per word: {check.time_limit_seconds} seconds",
            reply_markup=start_check_keyboard(check.id),
        )


@router.message(Command("resume"))
async def resume_check(message: Message, session: AsyncSession, bot: Bot) -> None:
    user = await _upsert_user(message, session)
    service = CheckingService(session)
    attempt = await service.get_active_attempt_for_user(user)
    if attempt is None:
        await message.answer("You do not have an active check to resume.")
        return
    question = await service.get_current_question(attempt.id)
    if question is None:
        result = await ResultService(session).get_attempt_result(attempt.id)
        await message.answer(format_student_result(result))
        return
    await _send_question(message.chat.id, question, attempt.total_questions, bot)
    _schedule_timeout(bot, message.chat.id, attempt.id, question.id)


@router.callback_query(F.data.startswith("student_start_check:"))
async def start_check(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    user = await _upsert_user(callback, session)
    check_id = int(str(callback.data).split(":", 1)[1])
    try:
        attempt = await CheckingService(session).start_attempt(check_id=check_id, user=user)
    except CheckFlowError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    question = await CheckingService(session).get_current_question(attempt.id)
    if question is None:
        await callback.answer("No question is available.", show_alert=True)
        return
    if callback.message:
        await _send_question(callback.message.chat.id, question, attempt.total_questions, bot)
        _schedule_timeout(bot, callback.message.chat.id, attempt.id, question.id)
    await callback.answer()


@router.message(F.text)
async def receive_answer(message: Message, session: AsyncSession, bot: Bot) -> None:
    if message.from_user is None or message.text is None:
        return
    user = await _upsert_user(message, session)
    service = CheckingService(session)
    attempt = await service.get_active_attempt_for_user(user)
    if attempt is None:
        return

    try:
        outcome = await service.submit_answer(
            attempt_id=attempt.id,
            answer=message.text,
            answered_at=datetime.now(UTC),
        )
    except CheckFlowError:
        await message.answer("That answer is no longer active. Use /resume to continue.")
        return

    await _send_outcome(message.chat.id, outcome, bot)


async def _send_question(chat_id: int, question: QuestionAttempt, total: int, bot: Bot) -> None:
    remaining_seconds = max(0, int((question.deadline - datetime.now(UTC)).total_seconds()))
    await bot.send_message(
        chat_id,
        f"Question {question.question_number}/{total}\n\n"
        f'What does "{question.vocabulary_item.word}" mean?\n\n'
        f"Time remaining: {remaining_seconds} seconds",
    )


async def _send_outcome(chat_id: int, outcome, bot: Bot) -> None:
    definition = outcome.question.vocabulary_item.definition
    if outcome.is_expired:
        await bot.send_message(chat_id, f"Time's up!\n\nCorrect answer:\n{definition}")
    elif outcome.is_correct:
        await bot.send_message(chat_id, "Correct!\n\n+1 point\n\nNext word...")
    else:
        await bot.send_message(
            chat_id, f"Incorrect.\n\nCorrect answer:\n{definition}\n\nNext word..."
        )

    if outcome.finished:
        async with async_session_factory() as session:
            result = await ResultService(session).get_attempt_result(
                outcome.question.check_attempt_id
            )
        await bot.send_message(chat_id, format_student_result(result))
        return

    if outcome.next_question is not None:
        await _send_question(
            chat_id, outcome.next_question, outcome.question.check_attempt.total_questions, bot
        )
        _schedule_timeout(bot, chat_id, outcome.question.check_attempt_id, outcome.next_question.id)


def _schedule_timeout(bot: Bot, chat_id: int, attempt_id: int, question_id: int) -> None:
    async def expire_later() -> None:
        async with async_session_factory() as session:
            try:
                service = CheckingService(session)
                question = await service.get_current_question(attempt_id)
                if question is None or question.id != question_id:
                    return
                sleep_for = max(0, (question.deadline - datetime.now(UTC)).total_seconds()) + 0.2
                await asyncio.sleep(sleep_for)
                outcome = await service.expire_current_question(
                    attempt_id=attempt_id, now=datetime.now(UTC)
                )
                if outcome is not None:
                    await _send_outcome(chat_id, outcome, bot)
            except Exception:
                logger.exception(
                    "question_timeout_task_failed", attempt_id=attempt_id, question_id=question_id
                )

    asyncio.create_task(expire_later())
