from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db import SessionLocal
from keyboards import mailbox_actions_keyboard, mailbox_list_keyboard
from repositories import MailboxRepository
from states import AddMailboxState, EditMailboxState
from handlers.common import ensure_access, is_allowed_user


router = Router()


def _ensure_user_id(message: Message) -> int:
    if not message.from_user:
        raise ValueError("Telegram user id was not found")
    return message.from_user.id


def _callback_user_id(callback: CallbackQuery) -> int | None:
    return callback.from_user.id if callback.from_user else None


async def _ensure_callback_access(callback: CallbackQuery) -> bool:
    user_id = _callback_user_id(callback)
    if user_id is None:
        await callback.answer("Не удалось определить пользователя", show_alert=True)
        return False
    if not is_allowed_user(user_id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return False
    return True


@router.message(Command("add_mail"))
async def add_mailbox_start(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.clear()
    await state.set_state(AddMailboxState.title)
    await message.answer("Введи внутреннее название почты. Например: Main Steam Mail")


@router.message(AddMailboxState.title)
async def add_mailbox_title(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AddMailboxState.email)
    await message.answer("Введи email ящика Outlook/Hotmail")


@router.message(AddMailboxState.email)
async def add_mailbox_email(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(email=(message.text or "").strip())
    await state.set_state(AddMailboxState.password)
    await message.answer("Введи пароль приложения или IMAP-пароль")


@router.message(AddMailboxState.password)
async def add_mailbox_password(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(password=(message.text or "").strip())
    await state.set_state(AddMailboxState.imap_host)
    await message.answer("Введи IMAP host. Для Outlook обычно: imap-mail.outlook.com")


@router.message(AddMailboxState.imap_host)
async def add_mailbox_imap_host(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    value = ((message.text or "").strip() or "imap-mail.outlook.com")
    await state.update_data(imap_host=value)
    await state.set_state(AddMailboxState.imap_port)
    await message.answer("Введи IMAP port. Обычно: 993")


@router.message(AddMailboxState.imap_port)
async def add_mailbox_imap_port(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Порт должен быть числом. Например: 993")
        return

    await state.update_data(imap_port=int(text))
    await state.set_state(AddMailboxState.account_type)
    await message.answer("Введи тип аккаунта: steam или faceit")


@router.message(AddMailboxState.account_type)
async def add_mailbox_account_type(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    value = (message.text or "").strip().lower()
    if value not in {"steam", "faceit"}:
        await message.answer("Допустимые значения: steam или faceit")
        return

    await state.update_data(account_type=value)
    await state.set_state(AddMailboxState.account_name)
    await message.answer("Введи имя аккаунта, которое будет отображаться в уведомлении")


@router.message(AddMailboxState.account_name)
async def add_mailbox_account_name(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    data = await state.get_data()
    owner_telegram_id = _ensure_user_id(message)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailbox = await repo.create_mailbox(
            owner_telegram_id=owner_telegram_id,
            title=data["title"],
            email=data["email"],
            password=data["password"],
            imap_host=data["imap_host"],
            imap_port=data["imap_port"],
            account_type=data["account_type"],
            account_name=(message.text or "").strip(),
        )

    await state.clear()
    await message.answer(f"Почта добавлена.\nID: {mailbox.id}\nНазвание: {mailbox.title}\nТип: {mailbox.account_type}")


@router.message(Command("list_mail"))
async def list_mailboxes(message: Message) -> None:
    if not await ensure_access(message):
        return
    owner_telegram_id = _ensure_user_id(message)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailboxes = await repo.list_by_owner(owner_telegram_id)

    if not mailboxes:
        await message.answer("Список почт пуст. Используй /add_mail")
        return

    lines = []
    for mailbox in mailboxes:
        status = "активна" if mailbox.is_active else "выключена"
        lines.append(f"{mailbox.id}. {mailbox.title} | {mailbox.email} | {mailbox.account_type} | {mailbox.account_name} | {status}")

    await message.answer("\n".join(lines), reply_markup=mailbox_list_keyboard(mailboxes))


@router.callback_query(F.data.startswith("mailbox:"))
async def mailbox_actions(callback: CallbackQuery) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    owner_telegram_id = _callback_user_id(callback)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailbox = await repo.get_by_id_for_owner(mailbox_id, owner_telegram_id)

    if not mailbox:
        await callback.message.answer("Почта не найдена или недоступна.")
        await callback.answer()
        return

    await callback.message.answer(
        f"Почта: {mailbox.title}\nEmail: {mailbox.email}\nТип: {mailbox.account_type}\nАккаунт: {mailbox.account_name}",
        reply_markup=mailbox_actions_keyboard(mailbox.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_mailbox(callback: CallbackQuery) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    owner_telegram_id = _callback_user_id(callback)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailbox = await repo.get_by_id_for_owner(mailbox_id, owner_telegram_id)
        if not mailbox:
            await callback.message.answer("Почта не найдена или недоступна.")
            await callback.answer()
            return
        mailbox = await repo.toggle_active(mailbox)

    status = "включена" if mailbox.is_active else "выключена"
    await callback.message.answer(f"Почта {mailbox.title} теперь {status}.")
    await callback.answer()


@router.callback_query(F.data.startswith("delete:"))
async def delete_mailbox(callback: CallbackQuery) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    owner_telegram_id = _callback_user_id(callback)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailbox = await repo.get_by_id_for_owner(mailbox_id, owner_telegram_id)
        if not mailbox:
            await callback.message.answer("Почта не найдена или недоступна.")
            await callback.answer()
            return
        title = mailbox.title
        await repo.delete(mailbox)

    await callback.message.answer(f"Почта {title} удалена.")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title:"))
async def edit_mailbox_title_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    await state.set_state(EditMailboxState.title)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.answer("Введи новое название почты")
    await callback.answer()


@router.message(EditMailboxState.title)
async def edit_mailbox_title_finish(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    data = await state.get_data()
    mailbox_id = data["mailbox_id"]
    owner_telegram_id = _ensure_user_id(message)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailbox = await repo.get_by_id_for_owner(mailbox_id, owner_telegram_id)
        if not mailbox:
            await message.answer("Почта не найдена или недоступна.")
            await state.clear()
            return
        mailbox = await repo.update_title(mailbox, (message.text or "").strip())

    await state.clear()
    await message.answer(f"Название обновлено: {mailbox.title}")


@router.callback_query(F.data.startswith("edit_account:"))
async def edit_mailbox_account_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    await state.set_state(EditMailboxState.account_name)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.answer("Введи новое имя аккаунта")
    await callback.answer()


@router.message(EditMailboxState.account_name)
async def edit_mailbox_account_finish(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    data = await state.get_data()
    mailbox_id = data["mailbox_id"]
    owner_telegram_id = _ensure_user_id(message)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailbox = await repo.get_by_id_for_owner(mailbox_id, owner_telegram_id)
        if not mailbox:
            await message.answer("Почта не найдена или недоступна.")
            await state.clear()
            return
        mailbox = await repo.update_account_name(mailbox, (message.text or "").strip())

    await state.clear()
    await message.answer(f"Имя аккаунта обновлено: {mailbox.account_name}")


@router.callback_query(F.data.startswith("edit_password:"))
async def edit_mailbox_password_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    await state.set_state(EditMailboxState.password)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.answer("Введи новый пароль приложения / IMAP-пароль")
    await callback.answer()


@router.message(EditMailboxState.password)
async def edit_mailbox_password_finish(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    data = await state.get_data()
    mailbox_id = data["mailbox_id"]
    owner_telegram_id = _ensure_user_id(message)

    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailbox = await repo.get_by_id_for_owner(mailbox_id, owner_telegram_id)
        if not mailbox:
            await message.answer("Почта не найдена или недоступна.")
            await state.clear()
            return
        await repo.update_password(mailbox, (message.text or "").strip())

    await state.clear()
    await message.answer("Пароль обновлен.")
