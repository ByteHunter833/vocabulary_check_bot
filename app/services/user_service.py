from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User, UserRole


@dataclass(frozen=True)
class TelegramUserData:
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_telegram_user(self, data: TelegramUserData) -> User:
        configured_role = self._configured_role(data.id)
        result = await self.session.execute(select(User).where(User.telegram_user_id == data.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_user_id=data.id,
                username=data.username,
                first_name=data.first_name,
                last_name=data.last_name,
                role=configured_role or UserRole.STUDENT,
            )
            self.session.add(user)
        else:
            user.username = data.username
            user.first_name = data.first_name
            user.last_name = data.last_name
            if configured_role is not None:
                user.role = configured_role

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def complete_student_registration(
        self, user: User, *, display_name: str, patronymic: str | None
    ) -> User:
        user.display_name = display_name.strip()
        user.patronymic = patronymic.strip() if patronymic else None
        user.registration_completed = True
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def add_admin_by_telegram_id(self, telegram_user_id: int) -> User:
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                username=None,
                first_name=None,
                last_name=None,
                role=UserRole.ADMIN,
                registration_completed=True,
            )
            self.session.add(user)
        elif user.role != UserRole.SUPER_ADMIN:
            user.role = UserRole.ADMIN
            user.registration_completed = True

        await self.session.commit()
        await self.session.refresh(user)
        return user

    def _configured_role(self, telegram_user_id: int) -> UserRole | None:
        if telegram_user_id in settings.super_admin_telegram_ids:
            return UserRole.SUPER_ADMIN
        if telegram_user_id in settings.admin_telegram_ids:
            return UserRole.ADMIN
        return None
