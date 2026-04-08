from __future__ import annotations

from cryptography.fernet import Fernet

from bot.config import get_settings


class Cipher:
    def __init__(self) -> None:
        key = get_settings().encryption_key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.decrypt(value.encode()).decode()