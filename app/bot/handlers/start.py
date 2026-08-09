from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin import admin_menu_keyboard
from app.bot.keyboards.checking import skip_patronymic_keyboard, student_menu_keyboard
from app.bot.states.registration import StudentRegistrationStates
from app.bot.utils import safe_edit_text
from app.models import UserRole
from app.services.user_service import TelegramUserData, UserService

router = Router()


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await state.clear()
    user = await UserService(session).upsert_telegram_user(
        TelegramUserData(
            id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    )
    if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        await send_admin_menu(message, user.role)
    elif not user.registration_completed:
        await state.set_state(StudentRegistrationStates.waiting_for_first_name)
        await message.answer("Welcome. Please enter your first name.")
    else:
        await send_student_menu(message)


@router.message(Command("menu"))
async def menu_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await UserService(session).upsert_telegram_user(
        TelegramUserData(
            id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    )
    if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        await send_admin_menu(message, user.role)
    elif user.registration_completed:
        await send_student_menu(message)
    else:
        await message.answer("Please finish registration first. Enter your first name.")


@router.message(StudentRegistrationStates.waiting_for_first_name, F.text)
async def receive_first_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Please enter a valid first name.")
        return
    await state.update_data(display_name=name)
    await state.set_state(StudentRegistrationStates.waiting_for_patronymic)
    await message.answer(
        "Patronymic is optional. Send it now or press Skip.",
        reply_markup=skip_patronymic_keyboard(),
    )


@router.message(StudentRegistrationStates.waiting_for_patronymic, F.text)
async def receive_patronymic(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    if message.from_user is None:
        return
    await finish_registration(
        message,
        state,
        session,
        telegram_user=message.from_user,
        patronymic=(message.text or "").strip(),
    )


@router.callback_query(
    StudentRegistrationStates.waiting_for_patronymic,
    F.data == "student_skip_patronymic",
)
async def skip_patronymic(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if callback.message:
        await finish_registration(
            callback.message,
            state,
            session,
            telegram_user=callback.from_user,
            patronymic=None,
        )
    await callback.answer()


@router.callback_query(F.data == "student_menu")
async def student_menu_callback(callback: CallbackQuery) -> None:
    if callback.message:
        await safe_edit_text(
            callback.message, "Student Menu", reply_markup=student_menu_keyboard()
        )
    await callback.answer()


async def finish_registration(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    telegram_user: TelegramUser,
    patronymic: str | None,
) -> None:
    data = await state.get_data()
    display_name = str(data.get("display_name") or "").strip()
    if not display_name:
        await state.set_state(StudentRegistrationStates.waiting_for_first_name)
        await message.answer("Please enter your first name.")
        return
    user = await UserService(session).upsert_telegram_user(
        TelegramUserData(
            id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )
    )
    await UserService(session).complete_student_registration(
        user, display_name=display_name, patronymic=patronymic
    )
    await state.clear()
    await message.answer("Registration completed.")
    await send_student_menu(message)


async def send_student_menu(message: Message) -> None:
    await message.answer("Student Menu", reply_markup=student_menu_keyboard())


async def send_admin_menu(message: Message, role: UserRole) -> None:
    await message.answer(
        "Admin Menu",
        reply_markup=admin_menu_keyboard(is_super_admin=role == UserRole.SUPER_ADMIN),
    )
