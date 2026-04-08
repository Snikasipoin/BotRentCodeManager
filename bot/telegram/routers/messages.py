from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.telegram.keyboards.main import MESSAGES, dialog_actions, dialogs_list_keyboard, main_menu
from bot.telegram.states.account import DialogReplyForm
from bot.services.funpay_dialogs import FunPayDialogService

router = Router()


async def _format_dialog(dialog) -> str:
    title = dialog.buyer_nickname or f"Chat {dialog.chat_id}"
    last_message = dialog.last_message_text or "-"
    updated = dialog.last_message_at.isoformat() if dialog.last_message_at else "-"
    order = f"\nЗаказ: #{dialog.current_order_id}" if dialog.current_order_id else ""
    return (
        f"💬 Диалог: {title}\n"
        f"Chat ID: {dialog.chat_id}{order}\n"
        f"Последнее сообщение: {last_message}\n"
        f"Обновлён: {updated}"
    )


async def _render_dialog_history(dialog_service: FunPayDialogService, chat_id: int) -> str:
    messages = await dialog_service.get_history(chat_id, limit=20)
    if not messages:
        return "История сообщений пока пуста."
    lines = [f"💬 История чата {chat_id}\n"]
    for message in messages:
        direction = "➡️" if message.direction == "outgoing" else "⬅️"
        prefix = f"{direction} {'BOT' if message.direction == 'outgoing' else 'BUYER'}"
        lines.append(f"{prefix}: {message.text}")
    return "\n".join(lines)


@router.message(Command("messages"))
@router.message(F.text == MESSAGES)
async def messages_menu(message: Message, dialog_service: FunPayDialogService) -> None:
    dialogs = await dialog_service.list_recent_dialogs(limit=10)
    if not dialogs:
        await message.answer("Пока нет сохранённых диалогов FunPay.", reply_markup=main_menu())
        return
    items = [
        (
            dialog.chat_id,
            dialog.buyer_nickname or f"Chat {dialog.chat_id}",
            dialog.last_message_text or "Без сообщений",
            dialog.last_message_at.isoformat() if dialog.last_message_at else "",
        )
        for dialog in dialogs
    ]
    await message.answer("💬 Последние диалоги FunPay", reply_markup=dialogs_list_keyboard(items))
    await message.answer("Главное меню", reply_markup=main_menu())


@router.callback_query(F.data == "dialog:list")
async def dialogs_list(callback: CallbackQuery, dialog_service: FunPayDialogService) -> None:
    await callback.answer()
    dialogs = await dialog_service.list_recent_dialogs(limit=10)
    if not dialogs:
        await callback.message.answer("Пока нет сохранённых диалогов FunPay.", reply_markup=main_menu())
        return
    items = [
        (
            dialog.chat_id,
            dialog.buyer_nickname or f"Chat {dialog.chat_id}",
            dialog.last_message_text or "Без сообщений",
            dialog.last_message_at.isoformat() if dialog.last_message_at else "",
        )
        for dialog in dialogs
    ]
    await callback.message.answer("💬 Последние диалоги FunPay", reply_markup=dialogs_list_keyboard(items))


@router.callback_query(F.data.startswith("dialog:view:"))
async def dialog_view(callback: CallbackQuery, dialog_service: FunPayDialogService) -> None:
    chat_id = int(callback.data.split(":")[-1])
    dialog = await dialog_service.get_dialog(chat_id)
    await callback.answer()
    if not dialog:
        await callback.message.answer("Диалог не найден.", reply_markup=main_menu())
        return
    await callback.message.answer(await _render_dialog_history(dialog_service, chat_id), reply_markup=dialog_actions(chat_id))


@router.callback_query(F.data.startswith("dialog:reply:"))
async def dialog_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    chat_id = int(callback.data.split(":")[-1])
    await state.set_state(DialogReplyForm.text)
    await state.update_data(chat_id=chat_id)
    await callback.answer()
    await callback.message.answer("Введите текст ответа для этого диалога")


@router.message(DialogReplyForm.text)
async def dialog_reply_send(message: Message, state: FSMContext, dialog_service: FunPayDialogService) -> None:
    data = await state.get_data()
    chat_id = int(data["chat_id"])
    await dialog_service.reply(chat_id, message.text.strip())
    await state.clear()
    await message.answer("Ответ отправлен.", reply_markup=main_menu())
