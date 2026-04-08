# Переменные окружения для деплоя

Ниже список значений, которые нужно добавить в личном кабинете хостинга / деплоя.

## Обязательные переменные

### `BOT_TOKEN`
Токен Telegram-бота от BotFather.

Пример:
```env
BOT_TOKEN=1234567890:AA...
```

### `ADMIN_ID`
Telegram ID владельца / администратора, который будет иметь доступ к панели.

Пример:
```env
ADMIN_ID=123456789
```

### `DATABASE_URL`
Строка подключения к PostgreSQL.

Пример:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/cs2_rent_bot
```

### `REDIS_URL`
Строка подключения к Redis.

Пример:
```env
REDIS_URL=redis://redis:6379/0
```

### `ENCRYPTION_KEY`
Ключ Fernet для шифрования паролей и чувствительных данных.

Сгенерировать:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Пример:
```env
ENCRYPTION_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx=
```

### `FUNPAY_GOLDEN_KEY`
Ваш `golden_key` из браузера FunPay.

Пример:
```env
FUNPAY_GOLDEN_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Рекомендуемые переменные

### `FUNPAY_USER_AGENT`
User-Agent того браузера, в котором был взят `golden_key`.

### `FUNPAY_POLL_INTERVAL`
Интервал опроса FunPay в секундах.

Рекомендуемое значение:
```env
FUNPAY_POLL_INTERVAL=3
```

### `EMAIL_IMAP_TIMEOUT`
Таймаут для IMAP-проверки почты.

Рекомендуемое значение:
```env
EMAIL_IMAP_TIMEOUT=20
```

### `REVIEW_BONUS_MINUTES`
Сколько минут добавлять за отзыв.

### `REMINDER_AFTER_MINUTES`
Через сколько минут после выдачи данных напоминать про отзыв.

### `EXPIRING_WARNING_MINUTES`
За сколько минут предупреждать о завершении аренды.

### `TZ`
Часовой пояс.

Пример:
```env
TZ=Europe/Moscow
```

### `LOG_LEVEL`
Уровень логирования.

Для продакшена:
```env
LOG_LEVEL=INFO
```

Для диагностики:
```env
LOG_LEVEL=DEBUG
```

## Что я рекомендую заполнить у вас на деплое

Минимально обязательно:
- `BOT_TOKEN`
- `ADMIN_ID`
- `DATABASE_URL`
- `REDIS_URL`
- `ENCRYPTION_KEY`
- `FUNPAY_GOLDEN_KEY`
- `FUNPAY_USER_AGENT`
- `TZ`
- `LOG_LEVEL`

Если хотите стабильный старт без сюрпризов, добавьте еще:
- `FUNPAY_POLL_INTERVAL=3`
- `EMAIL_IMAP_TIMEOUT=20`
- `REVIEW_BONUS_MINUTES=30`
- `REMINDER_AFTER_MINUTES=10`
- `EXPIRING_WARNING_MINUTES=5`