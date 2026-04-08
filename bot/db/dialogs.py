from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class FunPayDialog(Base):
    __tablename__ = "funpay_dialogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    buyer_nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    last_message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    current_order: Mapped[object | None] = relationship("Order", foreign_keys=[current_order_id])
    messages: Mapped[list[FunPayDialogMessage]] = relationship("FunPayDialogMessage", back_populates="dialog", cascade="all, delete-orphan")


class FunPayDialogMessage(Base):
    __tablename__ = "funpay_dialog_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(ForeignKey("funpay_dialogs.id", ondelete="CASCADE"), index=True)
    direction: Mapped[str] = mapped_column(Enum("incoming", "outgoing", name="funpay_message_direction"))
    text: Mapped[str] = mapped_column(Text)
    has_photo: Mapped[bool] = mapped_column(default=False)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dialog: Mapped[FunPayDialog] = relationship("FunPayDialog", back_populates="messages")
