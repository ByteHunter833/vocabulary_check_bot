from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from structlog import get_logger

from app.bot.handlers import admin, checking, start
from app.bot.middlewares.db import DatabaseSessionMiddleware
from app.core.config import settings

logger = get_logger(__name__)


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.update.middleware(DatabaseSessionMiddleware())
    dispatcher.include_router(start.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(checking.router)
    return dispatcher


async def run_bot_polling(stop_event: asyncio.Event) -> None:
    if not settings.bot_token:
        logger.warning("bot_token_missing_bot_polling_disabled")
        await stop_event.wait()
        return

    bot = Bot(token=settings.bot_token)
    dispatcher = create_dispatcher()
    polling_task = asyncio.create_task(dispatcher.start_polling(bot))
    stop_task = asyncio.create_task(stop_event.wait())
    done, pending = await asyncio.wait(
        {polling_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    for task in done:
        task.result()
    await bot.session.close()
