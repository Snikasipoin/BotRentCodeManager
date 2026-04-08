from __future__ import annotations

from pathlib import Path

from loguru import logger

from bot.funpay.client import FunPayClient, NewMessagePayload, NewOrderPayload
from bot.services.order_processor import OrderProcessor
from bot.services.runtime_config import RuntimeConfigService
from bot.telegram.keyboards.main import order_actions


class FunPayEventHandler:
    def __init__(self, client: FunPayClient, processor: OrderProcessor, config_service: RuntimeConfigService) -> None:
        self.client = client
        self.processor = processor
        self.config_service = config_service
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
            except Exception as exc:
                logger.exception("FunPay event processing failed: {}", exc)

    async def handle_new_order(self, payload: NewOrderPayload) -> None:
        await self.processor.create_order_from_funpay(
            funpay_order_id=payload.order_id,
            chat_id=payload.chat_id,
            buyer_nickname=payload.buyer_nickname,
            rental_minutes=payload.rental_minutes,
        )

    async def handle_new_message(self, payload: NewMessagePayload) -> None:
        if payload.has_photo and payload.order_id:
            photo_path = None
            if payload.photo_url:
                target = self.photos_dir / f"{payload.order_id}.jpg"
                photo_path = await self.client.download_photo(payload.photo_url, str(target))
            order = await self.processor.attach_photo(payload.order_id, payload.file_id, photo_path)
            if order:
                await self.processor.notify_admins(
                    f"Покупатель отправил фото для заказа {order.funpay_order_id}. Проверьте и выберите действие.",
                    reply_markup=order_actions(order.id),
                )
            return

        lowered = payload.text.lower().strip()
        triggers = await self.config_service.get_code_triggers()
        if any(trigger in lowered for trigger in triggers):
            answer = await self.processor.handle_code_request(payload.chat_id)
            await self.client.send_text(payload.chat_id, answer)
            return

        if "review" in lowered or "thanks" in lowered or "отзыв" in lowered:
            logger.info("Potential review-like message received: {}", payload.text)
