from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Any

import aiohttp
from loguru import logger

from bot.config import get_settings

try:
    from FunPayAPI import Account as FunPayAccount
    from FunPayAPI.updater.runner import Runner
except Exception:
    FunPayAccount = None
    Runner = None


@dataclass(slots=True)
class NewOrderPayload:
    order_id: str
    chat_id: int
    buyer_nickname: str
    rental_minutes: int


@dataclass(slots=True)
class NewMessagePayload:
    chat_id: int
    text: str
    has_photo: bool
    order_id: str | None = None
    file_id: str | None = None
    photo_url: str | None = None


class FunPayClient:
    DEFAULT_RENTAL_MINUTES = 60

    def __init__(self) -> None:
        self.settings = get_settings()
        self.account = None
        self.runner = None
        self.events_queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        self._stop = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    async def start(self) -> None:
        if FunPayAccount is None or Runner is None:
            logger.warning("FunPayAPI недоступна. Клиент FunPay будет работать в режиме заглушки.")
            return
        self._loop = asyncio.get_running_loop()
        self.account = FunPayAccount(self.settings.funpay_golden_key, self.settings.funpay_user_agent)
        self.account.get()
        self.runner = Runner(self.account)
        self._thread = threading.Thread(target=self._run_polling_sync, name="funpay-runner", daemon=True)
        self._thread.start()
        logger.info("FunPay client started")

    async def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            await asyncio.to_thread(self._thread.join, 5)

    def _run_polling_sync(self) -> None:
        if not self.runner or not self._loop:
            return
        while not self._stop.is_set():
            try:
                for event in self.runner.listen(requests_delay=self.settings.funpay_poll_interval):
                    if self._stop.is_set():
                        break
                    future = asyncio.run_coroutine_threadsafe(self._dispatch_raw_event(event), self._loop)
                    future.result()
            except Exception as exc:
                logger.exception("FunPay polling error: {}", exc)

    @staticmethod
    def _pick_attr(obj: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            value = getattr(obj, name, None)
            if value not in (None, "", []):
                return value
        return default

    @classmethod
    def _extract_rental_minutes(cls, event: Any) -> int:
        minutes = cls._pick_attr(
            event,
            "rental_minutes",
            "rent_minutes",
            "minutes",
            "duration_minutes",
            default=None,
        )
        if minutes is None:
            duration = cls._pick_attr(event, "duration", "rent_duration", default=None)
            if isinstance(duration, (int, float)):
                minutes = int(duration)
        try:
            minutes_int = int(minutes) if minutes is not None else cls.DEFAULT_RENTAL_MINUTES
        except (TypeError, ValueError):
            return cls.DEFAULT_RENTAL_MINUTES
        return minutes_int if minutes_int > 0 else cls.DEFAULT_RENTAL_MINUTES

    async def _dispatch_raw_event(self, event: Any) -> None:
        class_name = event.__class__.__name__
        logger.debug("FunPay event received: {} payload={}", class_name, getattr(event, "__dict__", repr(event)))
        if class_name == "NewOrderEvent":
            payload = NewOrderPayload(
                order_id=str(self._pick_attr(event, "order_id", "id", default="")),
                chat_id=int(self._pick_attr(event, "chat_id", "node_id", default=0) or 0),
                buyer_nickname=str(
                    self._pick_attr(
                        event,
                        "buyer_username",
                        "username",
                        "buyer",
                        "nickname",
                        default="buyer",
                    )
                ),
                rental_minutes=self._extract_rental_minutes(event),
            )
            await self.events_queue.put(("new_order", payload))
            return
        if class_name == "NewMessageEvent":
            message = self._pick_attr(event, "message", default=event)
            attachments = self._pick_attr(message, "attachments", default=[]) or []
            first_attachment = attachments[0] if attachments else None
            payload = NewMessagePayload(
                chat_id=int(self._pick_attr(event, "chat_id", "node_id", default=0) or 0),
                text=str(self._pick_attr(message, "text", default="") or ""),
                has_photo=bool(attachments),
                order_id=str(self._pick_attr(event, "order_id", "id", default="") or "") or None,
                file_id=str(self._pick_attr(first_attachment, "id", "file_id", default="") or "") or None,
                photo_url=str(self._pick_attr(first_attachment, "url", "download_url", default="") or "") or None,
            )
            await self.events_queue.put(("new_message", payload))

    async def send_text(self, chat_id: int | None, text: str) -> None:
        if not chat_id:
            return
        if not self.account:
            logger.info("[stub] FunPay -> {}: {}", chat_id, text)
            return
        await asyncio.to_thread(self.account.send_message, chat_id, text)

    async def download_photo(self, url: str, target_path: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                content = await response.read()
        with open(target_path, "wb") as file:
            file.write(content)
        return target_path
