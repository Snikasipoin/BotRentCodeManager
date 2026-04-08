from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Any

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
            logger.warning("FunPayAPI не доступна. Клиент FunPay будет работать в режиме заглушки.")
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

    async def _dispatch_raw_event(self, event: Any) -> None:
        class_name = event.__class__.__name__
        logger.debug("FunPay event received: {}", class_name)
        if class_name == "NewOrderEvent":
            payload = NewOrderPayload(
                order_id=str(getattr(event, "order_id", getattr(event, "id", ""))),
                chat_id=int(getattr(event, "node_id", getattr(event, "chat_id", 0))),
                buyer_nickname=str(getattr(event, "buyer_username", getattr(event, "username", "buyer"))),
                rental_minutes=int(getattr(event, "amount", 60) or 60),
            )
            await self.events_queue.put(("new_order", payload))
            return
        if class_name == "NewMessageEvent":
            message = getattr(event, "message", event)
            text = str(getattr(message, "text", "") or "")
            attachments = getattr(message, "attachments", None) or []
            first_attachment = attachments[0] if attachments else None
            payload = NewMessagePayload(
                chat_id=int(getattr(event, "chat_id", getattr(event, "node_id", 0))),
                text=text,
                has_photo=bool(attachments),
                order_id=str(getattr(event, "order_id", "") or "") or None,
                file_id=str(getattr(first_attachment, "id", "") or "") or None,
                photo_url=str(getattr(first_attachment, "url", "") or "") or None,
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
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                content = await response.read()
        with open(target_path, "wb") as file:
            file.write(content)
        return target_path