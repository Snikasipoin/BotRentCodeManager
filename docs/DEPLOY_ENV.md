# Переменные окружения для деплоя

## Обязательные

### BOT_TOKEN
Токен Telegram-бота от BotFather.

### ADMIN_ID
Список Telegram ID админов через запятую. Первый ID будет считаться основным для настроек и уведомлений, но доступ получат все указанные ID.

Пример:
```env
ADMIN_ID=123456789,987654321
```

### DATABASE_URL
Локальная SQLite-база внутри контейнера.

Пример:
```env
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
```

### ENCRYPTION_KEY
Ключ Fernet для шифрования секретов.

Сгенерировать:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### FUNPAY_GOLDEN_KEY
`golden_key` из браузера FunPay.

## Рекомендуемые

### FUNPAY_USER_AGENT
User-Agent браузера, где был взят `golden_key`.

### FUNPAY_POLL_INTERVAL
Интервал опроса FunPay в секундах.

### EMAIL_IMAP_TIMEOUT
Таймаут IMAP-проверки почты.

### REVIEW_BONUS_MINUTES
Сколько минут добавлять за отзыв.

### REMINDER_AFTER_MINUTES
Через сколько минут после выдачи данных напоминать про отзыв.

### EXPIRING_WARNING_MINUTES
За сколько минут предупреждать о завершении аренды.

### TZ
Часовой пояс, например `Europe/Moscow`.

### LOG_LEVEL
Уровень логирования. Обычно `INFO`, для отладки `DEBUG`.

## Что вставить в панели хостинга

Минимум:
- `BOT_TOKEN`
- `ADMIN_ID`
- `DATABASE_URL`
- `ENCRYPTION_KEY`
- `FUNPAY_GOLDEN_KEY`
- `FUNPAY_USER_AGENT`
- `TZ`
- `LOG_LEVEL`

Дополнительно для стабильной работы:
- `FUNPAY_POLL_INTERVAL=3`
- `EMAIL_IMAP_TIMEOUT=20`
- `REVIEW_BONUS_MINUTES=30`
- `REMINDER_AFTER_MINUTES=10`
- `EXPIRING_WARNING_MINUTES=5`
