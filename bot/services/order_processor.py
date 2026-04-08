from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.config import get_settings
from bot.db.enums import AccountStatus, OrderStatus
from bot.db.models import Account, Order, OrderLog
from bot.services.email_checker import EmailChecker
from bot.services.scheduler import SchedulerService
from bot.telegram.keyboards.main import order_actions
from bot.utils.encryption import Cipher
from bot.utils.helpers import fmt_dt, fmt_timedelta_minutes


class OrderProcessor:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], scheduler: SchedulerService, telegram_bot, funpay_client) -> None:
        self.session_factory = session_factory
        self.scheduler = scheduler
        self.telegram_bot = telegram_bot
        self.funpay_client = funpay_client
        self.settings = get_settings()
        self.email_checker = EmailChecker()
        self.cipher = Cipher()

    async def log(self, session: AsyncSession, order: Order, source: str, action: str, message: str, payload: str | None = None) -> None:
        session.add(OrderLog(order_id=order.id, source=source, action=action, message=message, payload_json=payload))

    async def create_order_from_funpay(self, funpay_order_id: str, chat_id: int, buyer_nickname: str, rental_minutes: int) -> Order:
        async with self.session_factory() as session:
            existing = await session.scalar(select(Order).where(Order.funpay_order_id == funpay_order_id))
            if existing:
                return existing
            order = Order(
                funpay_order_id=funpay_order_id,
                funpay_chat_id=chat_id,
                buyer_nickname=buyer_nickname,
                rental_minutes=rental_minutes,
                status=OrderStatus.PENDING_PHOTO,
            )
            session.add(order)
            await session.flush()
            await self.log(session, order, "funpay", "new_order", "New order created from FunPay")
            await session.commit()
            await session.refresh(order)

        await self.funpay_client.send_text(
            chat_id,
            "Accounts are rented only for PC clubs. Please send a confirmation photo as shown in the example.",
        )
        await self.notify_admin_new_order(order)
        return order

    async def notify_admin_new_order(self, order: Order) -> None:
        text = (
            "New FunPay order\n"
            f"Order: {order.funpay_order_id}\n"
            f"Buyer: {order.buyer_nickname}\n"
            f"Duration: {fmt_timedelta_minutes(order.rental_minutes)}\n"
            f"Status: {order.status.value}"
        )
        await self.telegram_bot.send_message(self.settings.admin_id, text, reply_markup=order_actions(order.id))

    async def attach_photo(self, funpay_order_id: str, file_id: str | None, photo_path: str | None) -> Order | None:
        async with self.session_factory() as session:
            order = await session.scalar(select(Order).where(Order.funpay_order_id == funpay_order_id))
            if not order:
                return None
            order.photo_file_id = file_id
            order.photo_path = photo_path
            await self.log(session, order, "funpay", "photo_received", "Photo received from buyer")
            await session.commit()
            await session.refresh(order)
            return order

    async def get_next_available_account(self, session: AsyncSession) -> Account | None:
        return await session.scalar(select(Account).where(Account.status == AccountStatus.AVAILABLE).order_by(Account.id.asc()))

    async def approve_photo(self, order_id: int) -> Order:
        async with self.session_factory() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            account = await self.get_next_available_account(session)
            if not account:
                raise ValueError("No available accounts")

            order.account_id = account.id
            order.status = OrderStatus.ACTIVE
            order.start_time = datetime.now(timezone.utc)
            order.end_time = order.start_time + timedelta(minutes=order.rental_minutes)
            account.status = AccountStatus.RENTED
            account.current_order_id = order.id
            await self.log(session, order, "telegram", "photo_approved", f"Photo approved, account #{account.id} assigned")
            await session.commit()
            await session.refresh(order)
            await session.refresh(account)

        await self.send_credentials(order, account)
        await self.schedule_order_jobs(order.id, order.start_time, order.end_time)
        return order

    async def reject_photo(self, order_id: int, reason: str = "Photo was rejected") -> Order:
        async with self.session_factory() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")
            order.status = OrderStatus.PHOTO_REJECTED
            await self.log(session, order, "telegram", "photo_rejected", reason)
            await session.commit()
        await self.funpay_client.send_text(order.funpay_chat_id, f"Photo check failed. {reason}")
        return order

    async def send_credentials(self, order: Order, account: Account) -> None:
        steam_password = self.cipher.decrypt(account.steam_password_encrypted) or ""
        faceit_password = self.cipher.decrypt(account.faceit_password_encrypted) or ""
        parts = [
            "Photo approved. Login details:",
            f"Steam login: {account.steam_login}",
            f"Steam password: {steam_password}",
        ]
        if account.faceit_login:
            parts.extend([
                f"Faceit login: {account.faceit_login}",
                f"Faceit password: {faceit_password}",
            ])
        parts.append(f"Rent active until: {fmt_dt(order.end_time)}")
        await self.funpay_client.send_text(order.funpay_chat_id, "\n".join(parts))

    async def schedule_order_jobs(self, order_id: int, start_time: datetime, end_time: datetime) -> None:
        reminder_at = start_time + timedelta(minutes=self.settings.reminder_after_minutes)
        warning_at = end_time - timedelta(minutes=self.settings.expiring_warning_minutes)
        self.scheduler.schedule_once(f"order:{order_id}:reminder", reminder_at, self.send_review_reminder, order_id)
        self.scheduler.schedule_once(f"order:{order_id}:warning", warning_at, self.send_expiring_warning, order_id)
        self.scheduler.schedule_once(f"order:{order_id}:finish", end_time, self.finish_order, order_id)

    async def restore_schedules(self) -> None:
        async with self.session_factory() as session:
            orders = (await session.scalars(select(Order).where(or_(Order.status == OrderStatus.ACTIVE, Order.status == OrderStatus.CREDS_SENT)))).all()
            for order in orders:
                if order.start_time and order.end_time:
                    await self.schedule_order_jobs(order.id, order.start_time, order.end_time)

    async def send_review_reminder(self, order_id: int) -> None:
        async with self.session_factory() as session:
            order = await session.get(Order, order_id)
            if not order or order.reminder_sent or not order.funpay_chat_id:
                return
            order.reminder_sent = True
            await self.log(session, order, "scheduler", "reminder", "Review reminder sent")
            await session.commit()
        await self.funpay_client.send_text(order.funpay_chat_id, "Please confirm the deal and leave a review.")

    async def send_expiring_warning(self, order_id: int) -> None:
        async with self.session_factory() as session:
            order = await session.get(Order, order_id)
            if not order or order.warning_sent or not order.funpay_chat_id:
                return
            order.warning_sent = True
            await self.log(session, order, "scheduler", "warning", "Expiry warning sent")
            await session.commit()
        await self.funpay_client.send_text(order.funpay_chat_id, f"Warning: the rent ends in {self.settings.expiring_warning_minutes} minutes.")

    async def finish_order(self, order_id: int) -> None:
        async with self.session_factory() as session:
            order = await session.get(Order, order_id)
            if not order:
                return
            if order.account_id:
                account = await session.get(Account, order.account_id)
                if account:
                    account.status = AccountStatus.AVAILABLE
                    account.current_order_id = None
            order.status = OrderStatus.COMPLETED
            await self.log(session, order, "scheduler", "completed", "Rent completed")
            await session.commit()
        if order.funpay_chat_id:
            await self.funpay_client.send_text(order.funpay_chat_id, "Rent time is over. Thanks for the order.")

    async def handle_code_request(self, chat_id: int) -> str:
        async with self.session_factory() as session:
            order = await session.scalar(select(Order).where(Order.funpay_chat_id == chat_id, Order.status == OrderStatus.ACTIVE).order_by(Order.id.desc()))
            if not order or not order.account_id:
                return "There is no active rent for this chat."
            account = await session.get(Account, order.account_id)
            if not account:
                return "Account for the order was not found."
            result = await self.email_checker.fetch_latest_code(account)
            if not result:
                return "No fresh code was found yet. Try again in a minute."
            await self.log(session, order, "funpay", "code_sent", f"Code sent: {result.provider}")
            await session.commit()
            return f"{result.provider.upper()} code: {result.code}"

    async def grant_review_bonus(self, order_id: int) -> None:
        async with self.session_factory() as session:
            order = await session.get(Order, order_id)
            if not order or order.extra_time_given or not order.end_time:
                return
            order.review_added = True
            order.extra_time_given = True
            order.review_bonus_minutes = self.settings.review_bonus_minutes
            order.end_time = order.end_time + timedelta(minutes=self.settings.review_bonus_minutes)
            await self.log(session, order, "funpay", "review_bonus", "Review bonus granted")
            await session.commit()
            await self.schedule_order_jobs(order.id, order.start_time or datetime.now(timezone.utc), order.end_time)
        if order.funpay_chat_id:
            await self.funpay_client.send_text(order.funpay_chat_id, f"Thanks for the review. {self.settings.review_bonus_minutes} minutes were added.")