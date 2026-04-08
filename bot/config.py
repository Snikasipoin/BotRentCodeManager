from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    admin_id_raw: str = Field(alias="ADMIN_ID")
    database_url: str = Field(default="sqlite+aiosqlite:///./data/bot.db", alias="DATABASE_URL")
    encryption_key: str = Field(alias="ENCRYPTION_KEY")
    funpay_golden_key: str = Field(alias="FUNPAY_GOLDEN_KEY")
    funpay_user_agent: str = Field(default="Mozilla/5.0", alias="FUNPAY_USER_AGENT")
    funpay_poll_interval: int = Field(default=3, alias="FUNPAY_POLL_INTERVAL")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    email_imap_timeout: int = Field(default=20, alias="EMAIL_IMAP_TIMEOUT")
    review_bonus_minutes: int = Field(default=30, alias="REVIEW_BONUS_MINUTES")
    reminder_after_minutes: int = Field(default=10, alias="REMINDER_AFTER_MINUTES")
    expiring_warning_minutes: int = Field(default=5, alias="EXPIRING_WARNING_MINUTES")
    timezone_name: str = Field(default="Europe/Moscow", alias="TZ")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: str) -> str:
        normalized = value.strip()
        Fernet(normalized.encode())
        return normalized

    @field_validator("admin_id_raw")
    @classmethod
    def validate_admin_ids(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ADMIN_ID must not be empty")
        admins = cls.parse_admin_ids(normalized)
        if not admins:
            raise ValueError("ADMIN_ID must contain at least one Telegram ID")
        return normalized

    @field_validator("funpay_poll_interval", "email_imap_timeout")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be positive")
        return value

    @staticmethod
    def parse_admin_ids(value: str) -> list[int]:
        admins: list[int] = []
        for part in value.split(","):
            normalized = part.strip()
            if not normalized:
                continue
            try:
                admin_id = int(normalized)
            except ValueError as exc:
                raise ValueError("ADMIN_ID must contain only numeric Telegram IDs separated by commas") from exc
            if admin_id not in admins:
                admins.append(admin_id)
        return admins

    @property
    def admin_id(self) -> list[int]:
        return self.parse_admin_ids(self.admin_id_raw)

    @property
    def primary_admin_id(self) -> int:
        return self.admin_id[0]

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_id

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()
