from functools import lru_cache
import os

from cryptography.fernet import Fernet
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(default="sqlite+aiosqlite:///./bot.db", alias="DATABASE_URL")
    encryption_key: str = Field(alias="ENCRYPTION_KEY")
    poll_interval_seconds: int = Field(default=15, alias="POLL_INTERVAL_SECONDS")
    owner_telegram_ids_raw: str = Field(default="", alias="OWNER_TELEGRAM_IDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        if not self.owner_telegram_ids_raw:
            self.owner_telegram_ids_raw = os.getenv("ADMIN_ID", "")

    @property
    def owner_telegram_ids(self) -> set[int]:
        return {
            int(item.strip())
            for item in self.owner_telegram_ids_raw.split(",")
            if item.strip()
        }

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        normalized = value.strip()
        try:
            Fernet(normalized.encode())
        except Exception as exc:
            raise ValueError(
                "ENCRYPTION_KEY must be a valid Fernet key. Generate it with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ) from exc
        return normalized

    @field_validator("poll_interval_seconds")
    @classmethod
    def validate_poll_interval(cls, value: int) -> int:
        if value < 5:
            raise ValueError("POLL_INTERVAL_SECONDS must be at least 5")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
