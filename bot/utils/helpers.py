from __future__ import annotations

from datetime import datetime


def markdown_escape(value: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    for char in escape_chars:
        value = value.replace(char, f"\\{char}")
    return value


def fmt_dt(value: datetime | None) -> str:
    if not value:
        return "-"
    return value.strftime("%d.%m.%Y %H:%M:%S")


def fmt_timedelta_minutes(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    if hours:
        return f"{hours} ч. {rest} мин."
    return f"{rest} мин."