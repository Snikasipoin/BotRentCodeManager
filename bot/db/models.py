from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base
from bot.db.enums import AccountStatus, OrderStatus


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    steam_login: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    steam_password_encrypted: Mapped[str] = mapped_column(Text)
    faceit_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    faceit_password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    email_password_encrypted: Mapped[str] = mapped_column(Text)
    email_imap_host: Mapped[str] = mapped_column(String(255), default="imap-mail.outlook.com")
    email_imap_port: Mapped[int] = mapped_column(Integer, default=993)
    status: Mapped[AccountStatus] = mapped_column(Enum(AccountStatus), default=AccountStatus.AVAILABLE, index=True)
    current_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    current_order: Mapped[Order | None] = relationship("Order", foreign_keys=[current_order_id], post_update=True)
    orders: Mapped[list[Order]] = relationship("Order", back_populates="account", foreign_keys="Order.account_id")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    funpay_order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    funpay_chat_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    buyer_nickname: Mapped[str] = mapped_column(String(255), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    rental_minutes: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING_PHOTO, index=True)
    review_added: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_time_given: Mapped[bool] = mapped_column(Boolean, default=False)
    review_bonus_minutes: Mapped[int] = mapped_column(Integer, default=0)
    warning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    account: Mapped[Account | None] = relationship("Account", back_populates="orders", foreign_keys=[account_id])
    logs: Mapped[list[OrderLog]] = relationship("OrderLog", back_populates="order", cascade="all, delete-orphan")


class OrderLog(Base, TimestampMixin):
    __tablename__ = "order_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    message: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship("Order", back_populates="logs")