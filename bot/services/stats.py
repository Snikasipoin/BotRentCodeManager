from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.enums import AccountStatus, OrderStatus
from bot.db.models import Account, Order


class StatsService:
    async def dashboard(self, session: AsyncSession) -> dict[str, int]:
        active_orders = await session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.ACTIVE))
        available_accounts = await session.scalar(select(func.count(Account.id)).where(Account.status == AccountStatus.AVAILABLE))
        rented_accounts = await session.scalar(select(func.count(Account.id)).where(Account.status == AccountStatus.RENTED))
        total_orders = await session.scalar(select(func.count(Order.id)))
        return {
            "active_orders": active_orders or 0,
            "available_accounts": available_accounts or 0,
            "rented_accounts": rented_accounts or 0,
            "total_orders": total_orders or 0,
        }

    async def period_stats(self, session: AsyncSession, days: int) -> dict[str, int]:
        start = datetime.now(timezone.utc) - timedelta(days=days)
        orders = await session.scalar(select(func.count(Order.id)).where(Order.created_at >= start))
        completed = await session.scalar(select(func.count(Order.id)).where(Order.created_at >= start, Order.status == OrderStatus.COMPLETED))
        cancelled = await session.scalar(select(func.count(Order.id)).where(Order.created_at >= start, Order.status == OrderStatus.CANCELLED))
        return {"orders": orders or 0, "completed": completed or 0, "cancelled": cancelled or 0}