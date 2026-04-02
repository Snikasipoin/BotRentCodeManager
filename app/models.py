from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Mailbox(Base):
    __tablename__ = "mailboxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), index=True)
    imap_host: Mapped[str] = mapped_column(String(255), default="imap-mail.outlook.com")
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    encrypted_password: Mapped[str] = mapped_column(Text)
    account_type: Mapped[str] = mapped_column(String(20), index=True)
    account_name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_seen_uid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    deliveries: Mapped[list["CodeDelivery"]] = relationship(back_populates="mailbox", cascade="all, delete-orphan")


class CodeDelivery(Base):
    __tablename__ = "code_deliveries"
    __table_args__ = (UniqueConstraint("mailbox_id", "message_uid", name="uq_mailbox_message_uid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mailbox_id: Mapped[int] = mapped_column(ForeignKey("mailboxes.id", ondelete="CASCADE"), index=True)
    message_uid: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(32))
    code_type: Mapped[str] = mapped_column(String(20), index=True)
    message_subject: Mapped[str] = mapped_column(String(255))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    mailbox: Mapped[Mailbox] = relationship(back_populates="deliveries")
