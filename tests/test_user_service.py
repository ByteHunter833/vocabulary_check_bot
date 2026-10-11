from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.config import settings
from app.models import User, UserRole
from app.services.user_service import TelegramUserData, UserService


@pytest_asyncio.fixture
async def user_sessions(monkeypatch):
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL user-service regression tests")

    # Isolate test data and enum types from the application's existing users.
    schema = f"test_users_{uuid4().hex}"
    engine = create_async_engine(
        database_url, connect_args={"server_settings": {"search_path": schema}}
    )
    monkeypatch.setattr(settings, "admin_telegram_ids_raw", "")
    monkeypatch.setattr(settings, "super_admin_telegram_ids_raw", "")
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            await connection.run_sync(User.__table__.create)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        try:
            async with engine.begin() as connection:
                await connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        finally:
            await engine.dispose()


async def test_new_user_has_student_role_and_registration_defaults(user_sessions):
    async with user_sessions() as session:
        user = await UserService(session).upsert_telegram_user(
            TelegramUserData(123, "student", "First", "Last")
        )

        assert user.id is not None
        assert user.telegram_user_id == 123
        assert user.role == UserRole.STUDENT
        assert user.registration_completed is False
        assert user.display_name is None


@pytest.mark.parametrize("role", list(UserRole))
async def test_repeated_start_preserves_role_and_registration(user_sessions, role):
    async with user_sessions() as session:
        existing = User(
            telegram_user_id=123,
            username="old",
            first_name="Old",
            role=role,
            display_name="Registered name",
            patronymic="Registered patronymic",
            registration_completed=True,
            updated_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        session.add(existing)
        await session.commit()
        original_id = existing.id
        created_at = existing.created_at

        for _ in range(2):
            user = await UserService(session).upsert_telegram_user(
                TelegramUserData(123, "new", "New", "Last")
            )
            assert user is existing
            assert user.id == original_id
            assert user.role == role
            assert (user.username, user.first_name, user.last_name) == ("new", "New", "Last")
            assert user.registration_completed is True
            assert user.display_name == "Registered name"
            assert user.patronymic == "Registered patronymic"
            assert user.created_at == created_at
            assert user.updated_at > datetime(2020, 1, 1, tzinfo=UTC)

        assert await session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize(
    ("admin_ids", "super_admin_ids", "role"),
    [("123", "", UserRole.ADMIN), ("123", "123", UserRole.SUPER_ADMIN)],
)
async def test_configured_roles_apply_to_new_and_existing_users(
    user_sessions, monkeypatch, admin_ids, super_admin_ids, role
):
    async with user_sessions() as session:
        service = UserService(session)
        data = TelegramUserData(123, None, "First", None)
        student = await service.upsert_telegram_user(data)
        assert student.role == UserRole.STUDENT
        monkeypatch.setattr(settings, "admin_telegram_ids_raw", admin_ids)
        monkeypatch.setattr(settings, "super_admin_telegram_ids_raw", super_admin_ids)
        assert (await service.upsert_telegram_user(data)).role == role

        # The same configuration also applies when the user has never started the bot.
        monkeypatch.setattr(settings, "admin_telegram_ids_raw", admin_ids.replace("123", "456"))
        monkeypatch.setattr(
            settings, "super_admin_telegram_ids_raw", super_admin_ids.replace("123", "456")
        )
        assert (
            await service.upsert_telegram_user(TelegramUserData(456, None, "Second", None))
        ).role == role


async def test_concurrent_starts_return_the_same_user(user_sessions):
    async def start():
        async with user_sessions() as session:
            user = await UserService(session).upsert_telegram_user(
                TelegramUserData(123, "student", "First", None)
            )
            return user.id

    ids = await asyncio.gather(*(start() for _ in range(8)))

    assert len(set(ids)) == 1
    async with user_sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_placeholder_names_are_cleared_on_update(user_sessions):
    async with user_sessions() as session:
        service = UserService(session)
        await service.upsert_telegram_user(TelegramUserData(123, "name", "First", "Last"))
        user = await service.upsert_telegram_user(TelegramUserData(123, ".", ".", None))

        assert user.username is None
        assert user.first_name is None
        assert user.last_name is None
