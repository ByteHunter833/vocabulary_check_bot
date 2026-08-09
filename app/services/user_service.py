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
        role = UserRole.ADMIN if data.id in settings.admin_telegram_ids else UserRole.STUDENT
        result = await self.session.execute(select(User).where(User.telegram_user_id == data.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_user_id=data.id,
                username=data.username,
                first_name=data.first_name,
                last_name=data.last_name,
                role=role,
            )
            self.session.add(user)
        else:
            user.username = data.username
            user.first_name = data.first_name
            user.last_name = data.last_name
            user.role = role

        await self.session.commit()
        await self.session.refresh(user)
        return user
