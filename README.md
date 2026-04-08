# CS2 Rent Bot for FunPay

Полноценный Telegram-бот для автоматизации аренды аккаунтов CS2 (Steam + Faceit) через FunPay.

## Что в проекте

- `bot/` - основное приложение
- `alembic/` - миграции БД
- `.env.example` - пример конфигурации
- `Dockerfile` и `docker-compose.yml` - контейнеризация
- `docs/DEPLOY_ENV.md` - что заполнять в переменных окружения на хостинге
- `docs/OUTLOOK_IMAP_SETUP.md` - как настраивать Outlook / Hotmail для получения кодов

## Основной стек

- Python 3.12+
- aiogram 3.x
- SQLAlchemy 2.x + Alembic
- SQLite внутри контейнера
- APScheduler
- FunPayAPI
- imap-tools
- loguru
- pydantic-settings
- cryptography
- Docker

## Быстрый старт

1. Скопируй `.env.example` в `.env`.
2. Сгенерируй ключ шифрования:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. Заполни `.env`.
4. Подними сервис:
   ```bash
   docker compose up --build -d
   ```
5. Примени миграции:
   ```bash
   docker compose exec bot alembic upgrade head
   ```

## Запуск без Docker

```bash
python -m venv .venv
pip install -r requirements.txt
alembic upgrade head
python -m bot.main
```

## Настройка FunPay

1. Авторизуйся в FunPay в браузере.
2. Открой DevTools -> Application -> Cookies.
3. Найди `golden_key`.
4. Скопируй его в `.env` как `FUNPAY_GOLDEN_KEY`.
5. При необходимости пропиши `FUNPAY_USER_AGENT` из того же браузера.

## Документация

- [DEPLOY_ENV.md](G:/MC/BOT_CODE/docs/DEPLOY_ENV.md)
- [OUTLOOK_IMAP_SETUP.md](G:/MC/BOT_CODE/docs/OUTLOOK_IMAP_SETUP.md)