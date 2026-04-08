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
    from FunPayAPI import enums as fp_enums
    from FunPayAPI.updater.runner import Runner
except Exception:
    FunPayAccount = None
    Runner = None
    fp_enums = None


@dataclass(slots=True)
class NewOrderPayload:
    order_id: str
    chat_id: int
    buyer_nickname: str
    rental_minutes: int
    description: str | None = None


@dataclass(slots=True)
class NewMessagePayload:
    chat_id: int
    text: str
    has_photo: bool
    buyer_nickname: str | None = None
    order_id: str | None = None
    file_id: str | None = None
    photo_url: str | None = None


@dataclass(slots=True)
class ChatSnapshotPayload:
    chat_id: int
    buyer_nickname: str | None
    last_message_text: str
    unread: bool


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
        await asyncio.to_thread(self.account.get)
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
                for event in self.runner.listen(requests_delay=self.settings.funpay_poll_interval, ignore_exceptions=False):
                    if self._stop.is_set():
                        break
                    future = asyncio.run_coroutine_threadsafe(self._dispatch_raw_event(event), self._loop)
                    future.result()
            except Exception as exc:
                logger.exception("FunPay polling error: {}", exc)

    @staticmethod
    def _pick_attr(obj: Any, *names: str, default: Any = None) -> Any:
        if obj is None:
            return default
        for name in names:
            if isinstance(obj, dict) and name in obj:
                value = obj.get(name)
                if value not in (None, "", []):
                    return value
            value = getattr(obj, name, None)
            if value not in (None, "", []):
                return value
        return default

    async def _resolve_chat_id(self, *, chat_id: int | None = None, buyer_nickname: str | None = None) -> int:
        if chat_id:
            return chat_id
        if not self.account or not buyer_nickname:
            return 0
        try:
            chat = await asyncio.to_thread(self.account.get_chat_by_name, buyer_nickname, True)
            return int(self._pick_attr(chat, "id", "chat_id", default=0) or 0)
        except Exception as exc:
            logger.warning("Failed to resolve FunPay chat by nickname {}: {}", buyer_nickname, exc)
            return 0

    @classmethod
    def _extract_rental_minutes(cls, order: Any) -> int:
        minutes = cls._pick_attr(order, "rental_minutes", "rent_minutes", "minutes", "duration_minutes", default=None)
        if minutes is None:
            duration = cls._pick_attr(order, "duration", "rent_duration", default=None)
            if isinstance(duration, (int, float)):
                minutes = int(duration)
        try:
            minutes_int = int(minutes) if minutes is not None else cls.DEFAULT_RENTAL_MINUTES
        except (TypeError, ValueError):
            return cls.DEFAULT_RENTAL_MINUTES
        return minutes_int if minutes_int > 0 else cls.DEFAULT_RENTAL_MINUTES

    async def _dispatch_raw_event(self, event: Any) -> None:
        event_type = self._pick_attr(event, "type", default=None)
        event_name = getattr(event_type, "name", None) if event_type is not None else event.__class__.__name__
        logger.debug("FunPay event received: {} payload={}", event_name, getattr(event, "__dict__", repr(event)))

        new_order_type = getattr(fp_enums.EventTypes, "NEW_ORDER", None) if fp_enums is not None else None
        new_message_type = getattr(fp_enums.EventTypes, "NEW_MESSAGE", None) if fp_enums is not None else None

        if new_order_type is not None and event_type == new_order_type:
            order = self._pick_attr(event, "order", default=None)
            buyer_nickname = str(self._pick_attr(order, "buyer_username", "buyer_name", "username", default="buyer"))
            order_id = str(self._pick_attr(order, "id", "order_id", default=""))
            chat_id = 0
            if self.account and buyer_nickname:
                try:
                    chat = await asyncio.to_thread(self.account.get_chat_by_name, buyer_nickname, True)
                    chat_id = int(self._pick_attr(chat, "id", "chat_id", default=0) or 0)
                except Exception as exc:
                    logger.warning("Failed to resolve chat by buyer nickname {}: {}", buyer_nickname, exc)
            payload = NewOrderPayload(
                order_id=order_id,
                chat_id=chat_id,
                buyer_nickname=buyer_nickname,
                rental_minutes=self._extract_rental_minutes(order),
                description=str(self._pick_attr(order, "description", "full_description", "title", default="") or "") or None,
            )
            logger.debug("FunPay new order parsed: order_id={}, chat_id={}, buyer={}", payload.order_id, payload.chat_id, payload.buyer_nickname)
            await self.events_queue.put(("new_order", payload))
            return

        if new_message_type is not None and event_type == new_message_type:
            message = self._pick_attr(event, "message", default=None)
            author_id = int(self._pick_attr(message, "author_id", "sender_id", default=0) or 0)
            if self.account and author_id == getattr(self.account, "id", None):
                return

            attachments = self._pick_attr(message, "attachments", "files", default=[]) or []
            first_attachment = attachments[0] if attachments else None
            buyer_nickname = str(self._pick_attr(message, "chat_name", "nickname", "author_name", default="") or "") or None
            text = str(self._pick_attr(message, "text", "body", "content", default="") or "")
            resolved_chat_id = await self._resolve_chat_id(
                chat_id=int(self._pick_attr(message, "chat_id", default=0) or 0),
                buyer_nickname=buyer_nickname,
            )
            payload = NewMessagePayload(
                chat_id=resolved_chat_id,
                text=text,
                has_photo=bool(attachments),
                buyer_nickname=buyer_nickname,
                order_id=str(self._pick_attr(message, "order_id", "order", default="") or "") or None,
                file_id=str(self._pick_attr(first_attachment, "id", "file_id", default="") or "") or None,
                photo_url=str(self._pick_attr(first_attachment, "url", "download_url", default="") or "") or None,
            )
            logger.debug(
                "FunPay new message parsed: chat_id={}, author_id={}, has_photo={}, text={}",
                payload.chat_id,
                author_id,
                payload.has_photo,
                payload.text,
            )
            await self.events_queue.put(("new_message", payload))
            return

        if fp_enums is not None:
            chat_event_types = {
                getattr(fp_enums.EventTypes, "INITIAL_CHAT", None),
                getattr(fp_enums.EventTypes, "LAST_CHAT_MESSAGE_CHANGED", None),
                getattr(fp_enums.EventTypes, "CHATS_LIST_CHANGED", None),
            }
            chat_event_types.discard(None)
            if event_type in chat_event_types:
                chat = self._pick_attr(event, "chat", default=None)
                if chat is None:
                    return
                payload = ChatSnapshotPayload(
                    chat_id=int(self._pick_attr(chat, "id", "chat_id", default=0) or 0),
                    buyer_nickname=str(self._pick_attr(chat, "name", default="") or "") or None,
                    last_message_text=str(self._pick_attr(chat, "last_message_text", default="") or ""),
                    unread=bool(self._pick_attr(chat, "unread", default=False)),
                )
                await self.events_queue.put(("chat_snapshot", payload))

    async def send_text(self, chat_id: int | None, text: str) -> None:
        if not chat_id:
            logger.warning("Skip FunPay send: empty chat_id for text={}", text)
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

