from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://vocab:vocab@localhost:5432/vocab"
    super_admin_telegram_ids_raw: str = Field(
        default="", validation_alias="SUPER_ADMIN_TELEGRAM_IDS"
    )
    admin_telegram_ids_raw: str = Field(default="", validation_alias="ADMIN_TELEGRAM_IDS")
    ocr_provider: str = "tesseract"
    ocr_api_key: str = ""
    app_env: str = "development"
    log_level: str = "INFO"
    default_time_limit_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def admin_telegram_ids(self) -> set[int]:
        if not self.admin_telegram_ids_raw:
            return set()
        return {
            int(item.strip()) for item in self.admin_telegram_ids_raw.split(",") if item.strip()
        }

    @property
    def super_admin_telegram_ids(self) -> set[int]:
        if not self.super_admin_telegram_ids_raw:
            return set()
        return {
            int(item.strip())
            for item in self.super_admin_telegram_ids_raw.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
