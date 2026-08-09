from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://vocab:vocab@localhost:5432/vocab"
    admin_telegram_ids_raw: str = Field(default="", validation_alias="ADMIN_TELEGRAM_IDS")
    ocr_provider: str = "tesseract"
    ocr_api_key: str = ""
    app_env: str = "development"
    log_level: str = "INFO"
    default_time_limit_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_telegram_ids(self) -> set[int]:
        if not self.admin_telegram_ids_raw:
            return set()
        return {
            int(item.strip()) for item in self.admin_telegram_ids_raw.split(",") if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
