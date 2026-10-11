from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.bot.keyboards.admin import (
    admin_checks_keyboard,
    admin_menu_keyboard,
    admin_results_keyboard,
    admin_students_keyboard,
    admin_vocabulary_preview_keyboard,
)
from app.bot.keyboards.checking import start_check_keyboard
from app.bot.states.admin import AdminManagementStates, AdminVocabularyStates
from app.bot.utils import (
    format_admin_results,
    format_individual_admin_result,
    safe_edit_text,
)
from app.core.config import settings
from app.models import User, UserRole
from app.services.checking_service import CheckingService
from app.services.ocr_service import OCRServiceError, build_ocr_service
from app.services.result_service import ResultService
from app.services.user_service import TelegramUserData, UserService
from app.services.vocabulary_service import (
    ParsedVocabularyItem,
    VocabularyParseError,
    VocabularyService,
    parse_vocabulary_text,
)

router = Router()
logger = get_logger(__name__)


async def _current_user(message: Message, session: AsyncSession) -> User | None:
    if message.from_user is None:
        return None
    return await UserService(session).upsert_telegram_user(
        TelegramUserData(
            id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    )


async def _require_admin(message: Message, session: AsyncSession) -> User | None:
    user = await _current_user(message, session)
    if user is None:
        return None
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        await message.answer("This command is available to admins only.")
        return None
    return user


async def _callback_user(callback: CallbackQuery, session: AsyncSession) -> User:
    return await UserService(session).upsert_telegram_user(
        TelegramUserData(
            id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
    )


async def _require_admin_callback(
    callback: CallbackQuery, session: AsyncSession
) -> User | None:
    user = await _callback_user(callback, session)
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        await callback.answer("Admins only.", show_alert=True)
        return None
    return user


async def _require_super_admin_callback(
    callback: CallbackQuery, session: AsyncSession
) -> User | None:
    user = await _callback_user(callback, session)
    if user.role != UserRole.SUPER_ADMIN:
        await callback.answer("Super admin only.", show_alert=True)
        return None
    return user


@router.message(Command("admin"))
async def admin_menu_command(message: Message, session: AsyncSession) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    await message.answer(
        "Admin Menu",
        reply_markup=admin_menu_keyboard(is_super_admin=user.role == UserRole.SUPER_ADMIN),
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin_callback(callback, session)
    if user is None:
        return
    if callback.message:
        await safe_edit_text(
            callback.message,
            "Admin Menu",
            reply_markup=admin_menu_keyboard(is_super_admin=user.role == UserRole.SUPER_ADMIN),
        )
    await callback.answer()


@router.message(Command("new_check"))
async def new_check_command(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    await state.set_state(AdminVocabularyStates.waiting_for_vocabulary)
    await message.answer(
        "Send a vocabulary list as text or as a photo.\n\n"
        "Example:\n"
        "predator - an animal that hunts other animals\n"
        "habitat - the natural home of an animal or plant"
    )


@router.callback_query(F.data == "admin_new_check")
async def new_check_callback(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _require_admin_callback(callback, session)
    if user is None:
        return
    await state.set_state(AdminVocabularyStates.waiting_for_vocabulary)
    if callback.message:
        await callback.message.answer(
            "Send a vocabulary list as text or as a photo.\n\n"
            "Example:\n"
            "predator - an animal that hunts other animals\n"
            "habitat - the natural home of an animal or plant"
        )
    await callback.answer()


@router.message(AdminVocabularyStates.waiting_for_vocabulary, F.text)
async def receive_vocabulary_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    user = await _require_admin(message, session)
    if user is None or message.text is None:
        return
    await _parse_and_preview(message, state, message.text)


@router.message(AdminVocabularyStates.waiting_for_vocabulary, F.photo)
async def receive_vocabulary_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    user = await _require_admin(message, session)
    if user is None or not message.photo:
        return
    try:
        buffer = await bot.download(message.photo[-1].file_id)
        if buffer is None:
            raise OCRServiceError("Telegram photo download failed.")
        image_bytes = buffer.read()
        extracted_text = await build_ocr_service(settings.ocr_provider).extract_text(image_bytes)
    except OCRServiceError:
        logger.exception("ocr_failed")
        await message.answer(
            "I could not extract vocabulary from that image. "
            "Please send the list as text or try a clearer image."
        )
        return
    await _parse_and_preview(message, state, extracted_text)


async def _parse_and_preview(message: Message, state: FSMContext, text: str) -> None:
    try:
        parsed_items = parse_vocabulary_text(text)
    except VocabularyParseError as exc:
        await message.answer(f"Could not parse the vocabulary list.\n\n{exc}")
        return

    title = f"Vocabulary Check {message.date.strftime('%Y-%m-%d %H:%M')}"
    await state.update_data(
        title=title,
        items=[item.__dict__ for item in parsed_items],
    )
    await state.set_state(AdminVocabularyStates.confirming_vocabulary)
    preview = "\n".join(f"{item.word} - {item.definition}" for item in parsed_items[:5])
    await message.answer(
        f"Vocabulary list created\n\nWords: {len(parsed_items)}\n\nPreview:\n{preview}",
        reply_markup=admin_vocabulary_preview_keyboard(),
    )


@router.callback_query(AdminVocabularyStates.confirming_vocabulary, F.data == "admin_vocab_preview")
async def preview_vocabulary(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    items = data.get("items", [])
    preview = "\n".join(f"{item['word']} - {item['definition']}" for item in items)
    if callback.message:
        await callback.message.answer(preview[:3900] or "No preview available.")
    await callback.answer()


@router.callback_query(AdminVocabularyStates.confirming_vocabulary, F.data == "admin_vocab_cancel")
async def cancel_vocabulary(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer("Vocabulary upload cancelled.")
    await callback.answer()


@router.callback_query(AdminVocabularyStates.confirming_vocabulary, F.data == "admin_vocab_publish")
async def publish_vocabulary(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if callback.from_user is None:
        return
    admin = await UserService(session).upsert_telegram_user(
        TelegramUserData(
            id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
    )
    if admin.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        await callback.answer("Admins only.", show_alert=True)
        return

    data = await state.get_data()
    title = str(data.get("title") or "Vocabulary Check")
    item_data = data.get("items", [])
    if not item_data:
        await callback.answer("No vocabulary to publish.", show_alert=True)
        return

    parsed_items = [
        ParsedVocabularyItem(
            word=item["word"],
            definition=item["definition"],
            accepted_answers=item["accepted_answers"],
            keywords=item["keywords"],
        )
        for item in item_data
    ]
    vocabulary_list = await VocabularyService(session).create_list(
        title=title,
        creator=admin,
        parsed_items=parsed_items,
    )
    check = await CheckingService(session).publish_check(
        vocabulary_list=vocabulary_list,
        title=title,
        time_limit_seconds=settings.default_time_limit_seconds,
    )

    students_result = await session.execute(
        select(User).where(
            User.role == UserRole.STUDENT,
            User.registration_completed.is_(True),
        )
    )
    students = list(students_result.scalars())
    question_count = min(settings.questions_per_check, len(item_data))
    for student in students:
        try:
            await bot.send_message(
                student.telegram_user_id,
                "Vocabulary Check\n\n"
                f"You have {question_count} words to check.\n\n"
                f"You will have {check.time_limit_seconds} seconds for each word.\n\n"
                "Are you ready?",
                reply_markup=start_check_keyboard(check.id),
            )
        except Exception:
            logger.exception(
                "student_notification_failed",
                student_id=student.telegram_user_id,
                check_id=check.id,
            )

    await state.clear()
    if callback.message:
        await callback.message.answer(
            f"Check published.\n\nCheck ID: {check.id}\nStudents notified: {len(students)}"
        )
    await callback.answer()


@router.message(Command("results"))
async def results_command(message: Message, session: AsyncSession) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    await _legacy_direct_result(message, session)


@router.callback_query(F.data == "admin_choose_results")
async def choose_results_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin_callback(callback, session)
    if user is None:
        return
    checks = await CheckingService(session).list_published_checks()
    if callback.message:
        if not checks:
            await safe_edit_text(
                callback.message,
                "No checks published yet.",
                reply_markup=admin_menu_keyboard(is_super_admin=user.role == UserRole.SUPER_ADMIN),
            )
        else:
            await safe_edit_text(
                callback.message,
                "Choose check",
                reply_markup=admin_checks_keyboard(checks),
            )
    await callback.answer()


async def send_check_picker(message: Message, session: AsyncSession) -> None:
    checks = await CheckingService(session).list_published_checks()
    if not checks:
        await message.answer("No checks published yet.")
        return
    await message.answer("Choose check", reply_markup=admin_checks_keyboard(checks))


@router.callback_query(F.data.startswith("admin_results:"))
async def refresh_results(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin_callback(callback, session)
    if user is None:
        return
    check_id = int(str(callback.data).split(":", 1)[1])
    results = await ResultService(session).get_check_results(check_id)
    if callback.message:
        await safe_edit_text(
            callback.message,
            format_admin_results(results),
            reply_markup=admin_students_keyboard(results),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_student_result:"))
async def student_result_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin_callback(callback, session)
    if user is None:
        return
    attempt_id = int(str(callback.data).split(":", 1)[1])
    result = await ResultService(session).get_attempt_result(attempt_id)
    if callback.message:
        await callback.message.answer(format_individual_admin_result(result))
    await callback.answer()


@router.callback_query(F.data == "super_add_admin")
async def add_admin_callback(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _require_super_admin_callback(callback, session)
    if user is None:
        return
    await state.set_state(AdminManagementStates.waiting_for_admin_telegram_id)
    if callback.message:
        await callback.message.answer("Send the Telegram numeric user ID for the new admin.")
    await callback.answer()


@router.message(Command("add_admin"))
async def add_admin_command(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    if user.role != UserRole.SUPER_ADMIN:
        await message.answer("This command is available to super admins only.")
        return
    await state.set_state(AdminManagementStates.waiting_for_admin_telegram_id)
    await message.answer("Send the Telegram numeric user ID for the new admin.")


@router.message(AdminManagementStates.waiting_for_admin_telegram_id, F.text)
async def receive_admin_id(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    if user.role != UserRole.SUPER_ADMIN:
        await message.answer("This command is available to super admins only.")
        await state.clear()
        return
    raw_id = (message.text or "").strip()
    if not raw_id.isdigit():
        await message.answer("Please send only a numeric Telegram user ID.")
        return
    new_admin = await UserService(session).add_admin_by_telegram_id(int(raw_id))
    await state.clear()
    await message.answer(
        f"Admin access granted.\n\nTelegram ID: {new_admin.telegram_user_id}"
    )


async def _legacy_direct_result(message: Message, session: AsyncSession) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await send_check_picker(message, session)
        return
    check_id = int(parts[1])
    if check_id > 2_147_483_647:
        await send_check_picker(message, session)
        return
    results = await ResultService(session).get_check_results(check_id)
    await message.answer(
        format_admin_results(results), reply_markup=admin_results_keyboard(check_id)
    )
