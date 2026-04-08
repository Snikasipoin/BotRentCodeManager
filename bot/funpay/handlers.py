from __future__ import annotations

from pathlib import Path

from loguru import logger
from sqlalchemy import select

from bot.db.models import Order
from bot.funpay.client import ChatSnapshotPayload, FunPayClient, NewMessagePayload, NewOrderPayload
from bot.services.funpay_dialogs import FunPayDialogService
from bot.services.order_processor import OrderProcessor
from bot.telegram.keyboards.main import order_actions


class FunPayEventHandler:
    def __init__(self, client: FunPayClient, processor: OrderProcessor, dialog_service: FunPayDialogService) -> None:
        self.client = client
        self.processor = processor
        self.dialog_service = dialog_service
        self.photos_dir = Path("storage/photos")
        self.photos_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        while True:
            event_type, payload = await self.client.events_queue.get()
            try:
                if event_type == "new_order":
                    await self.handle_new_order(payload)
                elif event_type == "new_message":
                    await self.handle_new_message(payload)
                elif event_type == "chat_snapshot":
                    await self.handle_chat_snapshot(payload)
            except Exception as exc:
                logger.exception("FunPay event processing failed: {}", exc)

    async def handle_chat_snapshot(self, payload: ChatSnapshotPayload) -> None:
        if not payload.chat_id:
            return
        await self.dialog_service.ensure_dialog(
            payload.chat_id,
            buyer_nickname=payload.buyer_nickname,
        )
        if payload.last_message_text:
            await self.dialog_service.record_incoming(
                payload.chat_id,
                payload.last_message_text,
                buyer_nickname=payload.buyer_nickname,
                has_photo=False,
            )

    async def handle_new_order(self, payload: NewOrderPayload) -> None:
        await self.processor.create_order_from_funpay(
            funpay_order_id=payload.order_id,
            chat_id=payload.chat_id,
            buyer_nickname=payload.buyer_nickname,
            rental_minutes=payload.rental_minutes,
        )

    async def handle_new_message(self, payload: NewMessagePayload) -> None:
        chat_id = payload.chat_id
        if not chat_id and payload.order_id:
            async with self.processor.session_factory() as session:
                order = await session.scalar(select(Order).where(Order.funpay_order_id == payload.order_id))
                if order and order.funpay_chat_id:
                    chat_id = int(order.funpay_chat_id)

        if payload.has_photo and payload.order_id:
            photo_path = None
            if payload.photo_url:
                target = self.photos_dir / f"{payload.order_id}.jpg"
                photo_path = await self.client.download_photo(payload.photo_url, str(target))
            order = await self.processor.attach_photo(payload.order_id, payload.file_id, photo_path)
            if order:
                if not chat_id and order.funpay_chat_id:
                    chat_id = int(order.funpay_chat_id)
                await self.processor.notify_admins(
                    f"Покупатель отправил фото для заказа {order.funpay_order_id}. Проверьте и выберите действие.",
                    reply_markup=order_actions(order.id),
                )
            if chat_id:
                await self.dialog_service.record_incoming(
                    chat_id,
                    payload.text,
                    buyer_nickname=payload.buyer_nickname,
                    has_photo=True,
                    photo_path=photo_path,
                )
            return

        if chat_id:
            await self.dialog_service.record_incoming(
                chat_id,
                payload.text,
                buyer_nickname=payload.buyer_nickname,
                has_photo=False,
            )

        lowered = (payload.text or "").lower().strip()
        triggers = await self.processor.config_service.get_code_triggers()
        if chat_id and triggers and any(trigger in lowered for trigger in triggers):
            answer = await self.processor.handle_code_request(chat_id)
            await self.client.send_text(chat_id, answer)
            await self.dialog_service.record_outgoing(chat_id, answer)
            return

        if "review" in lowered or "thanks" in lowered or "отзыв" in lowered:
            logger.info("Potential review-like message received: {}", payload.text)
