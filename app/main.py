from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from structlog import get_logger

from app.api.routes import checks, health
from app.bot.app import run_bot_polling
from app.core.logging import configure_logging

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    stop_event = asyncio.Event()
    bot_task = asyncio.create_task(run_bot_polling(stop_event))
    logger.info("application_started")
    try:
        yield
    finally:
        stop_event.set()
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        logger.info("application_stopped")


app = FastAPI(title="Telegram Vocabulary Check Bot", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(checks.router)
