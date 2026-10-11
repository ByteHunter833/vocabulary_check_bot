from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User, UserRole


@dataclass(frozen=True)
class TelegramUserData:
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None

    @classmethod
    def from_telegram_user(cls, telegram_user) -> TelegramUserData:
        cleaned_first_name = (
            None
            if not telegram_user.first_name or telegram_user.first_name.strip() == "."
            else telegram_user.first_name.strip()
        )
        cleaned_last_name = None if not telegram_user.last_name else telegram_user.last_name.strip()
        cleaned_username = None if not telegram_user.username else telegram_user.username.strip()

        return cls(
            id=telegram_user.id,
            username=cleaned_username,
            first_name=cleaned_first_name,
            last_name=cleaned_last_name,
        )


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_telegram_user(self, data: TelegramUserData) -> User:
        configured_role = self._configured_role(data.id)
        role = configured_role or UserRole.STUDENT

        cleaned_first_name = None if data.first_name == "." else data.first_name
        cleaned_username = None if data.username == "." else data.username

        updates = {
            "username": cleaned_username,
            "first_name": cleaned_first_name,
            "last_name": data.last_name,
            "updated_at": func.now(),
        }
        if configured_role is not None:
            updates["role"] = configured_role

        # Let PostgreSQL resolve duplicate and concurrent registrations atomically.
        stmt = (
            insert(User)
            .values(
                telegram_user_id=data.id,
                username=cleaned_username,
                first_name=cleaned_first_name,
                last_name=data.last_name,
                role=role,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_user_id],
                set_=updates,
            )
            .returning(User)
        )

        result = await self.session.execute(stmt)
        user = result.scalar_one()
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
