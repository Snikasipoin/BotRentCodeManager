from cryptography.fernet import Fernet

from app.config import get_settings


class SecretCipher:
    def __init__(self) -> None:
        settings = get_settings()
        self._fernet = Fernet(settings.encryption_key.encode())

    def encrypt(self, raw_value: str) -> str:
        return self._fernet.encrypt(raw_value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        return self._fernet.decrypt(encrypted_value.encode()).decode()
