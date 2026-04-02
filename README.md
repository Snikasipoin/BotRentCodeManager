# Telegram bot для кодов Steam Guard и FACEIT

## Что умеет

- добавлять много почтовых ящиков Outlook / Hotmail;
- хранить отдельное имя аккаунта и тип аккаунта (`steam` или `faceit`);
- включать и отключать автоматическую проверку;
- удалять и редактировать почты через Telegram;
- автоматически искать коды в письмах и присылать их в Telegram;
- не дублировать уже отправленные коды.

## Важное замечание по Outlook / Hotmail

Для Outlook / Hotmail надежнее использовать пароль приложения и IMAP, если на аккаунте включена двухфакторная аутентификация.

Рекомендуемые параметры:

- `imap_host`: `imap-mail.outlook.com`
- `imap_port`: `993`

Если Microsoft ограничит доступ по IMAP для конкретного аккаунта, следующим шагом нужно будет перейти на Microsoft Graph + OAuth. Архитектура проекта уже разделена на слои, поэтому такую замену можно сделать без переписывания Telegram-части.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Настройка `.env`

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=sqlite+aiosqlite:///./bot.db
ENCRYPTION_KEY=replace_with_fernet_key
POLL_INTERVAL_SECONDS=15
ADMIN_ID=123456789,987654321
```

- `ADMIN_ID` поддерживает один или несколько Telegram ID через запятую;
- секреты хранятся только в локальном `.env` и не должны коммититься в git.

## Генерация ключа шифрования

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Скопируй значение в `ENCRYPTION_KEY`.

## Запуск

Основной и рекомендуемый вариант:

```bash
python main.py
```

Если хостинг запускает файл напрямую через `python main.py`, проект тоже стартует корректно: `main.py` сам добавляет корень проекта в `sys.path`.

## Команды бота

- `/start` - старт и краткая справка
- `/help` - список команд
- `/add_mail` - добавить почту
- `/list_mail` - показать все почты
- `/cancel` - отменить текущее действие

## Архитектура

- `main.py` - точка входа
- `config.py` - конфигурация
- `db.py` - подключение к БД
- `models.py` - SQLAlchemy-модели
- `repositories.py` - работа с данными
- `handlers/` - Telegram handlers
- `services/imap_client.py` - чтение писем через IMAP
- `services/code_parser.py` - поиск кодов Steam Guard / FACEIT
- `services/poller.py` - фоновая проверка почт

## Безопасность

- пароли почты хранятся в БД в зашифрованном виде через `Fernet`;
- можно ограничить доступ к боту через `ADMIN_ID` или `OWNER_TELEGRAM_IDS`;
- каждый пользователь видит и редактирует только свои почты;
- уже обработанные письма не отправляются повторно.

## Что улучшить дальше

- перейти с SQLite на PostgreSQL для продакшена;
- вынести фонового воркера в отдельный процесс;
- добавить Redis для очередей и блокировок;
- заменить IMAP на Microsoft Graph OAuth;
- добавить аудит действий и rate limiting;
- добавить healthcheck, Docker и Alembic миграции.
