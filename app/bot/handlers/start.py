from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserRole
from app.services.user_service import TelegramUserData, UserService

router = Router()


@router.message(Command("start"))
async def start_command(message: Message, session: AsyncSession) -> None:
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
    if user.role == UserRole.ADMIN:
        await message.answer(
            "Welcome, admin.\n\n"
            "Use /new_check to upload vocabulary.\n"
            "Use /results <check_id> to view results."
        )
    else:
        await message.answer("Welcome. Use /checks to see available vocabulary checks.")
