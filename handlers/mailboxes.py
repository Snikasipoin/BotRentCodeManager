from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db import SessionLocal
from handlers.common import ensure_access, is_allowed_user, send_main_menu
from keyboards import ADD_MAIL_LABEL, LIST_MAIL_LABEL, mailbox_actions_keyboard, mailbox_list_keyboard, main_menu_keyboard
from repositories import MailboxRepository
from states import AddMailboxState, EditMailboxState


router = Router()


def _ensure_user_id(message: Message) -> int:
    if not message.from_user:
        raise ValueError("Telegram user id was not found")
    return message.from_user.id


def _callback_user_id(callback: CallbackQuery) -> int | None:
    return callback.from_user.id if callback.from_user else None


def _mailbox_summary(mailbox) -> str:
    status = "\u0430\u043a\u0442\u0438\u0432\u043d\u0430" if mailbox.is_active else "\u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d\u0430"
    return (
        f"\u041f\u043e\u0447\u0442\u0430: {mailbox.title}\n"
        f"Email: {mailbox.email}\n"
        f"\u0410\u043a\u043a\u0430\u0443\u043d\u0442: {mailbox.account_name}\n"
        f"\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043a\u043e\u0434\u043e\u0432: Steam + FACEIT \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438\n"
        f"\u0421\u0442\u0430\u0442\u0443\u0441: {status}"
    )


async def _show_mailbox_list(message: Message, owner_telegram_id: int) -> None:
    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailboxes = await repo.list_by_owner(owner_telegram_id)

    if not mailboxes:
        await message.answer(
            "\u0421\u043f\u0438\u0441\u043e\u043a \u043f\u043e\u0447\u0442 \u043f\u0443\u0441\u0442. \u041d\u0430\u0436\u043c\u0438 \u00ab\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043e\u0447\u0442\u0443\u00bb, \u0447\u0442\u043e\u0431\u044b \u043d\u0430\u0447\u0430\u0442\u044c.",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = []
    for mailbox in mailboxes:
        status = "\u0430\u043a\u0442\u0438\u0432\u043d\u0430" if mailbox.is_active else "\u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d\u0430"
        lines.append(f"{mailbox.id}. {mailbox.title} | {mailbox.email} | {mailbox.account_name} | {status}")

    await message.answer(
        "\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043d\u044b\u0435 \u043f\u043e\u0447\u0442\u044b:\n\n" + "\n".join(lines),
        reply_markup=mailbox_list_keyboard(mailboxes),
    )


async def _ensure_callback_access(callback: CallbackQuery) -> bool:
    user_id = _callback_user_id(callback)
    if user_id is None:
        await callback.answer("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f", show_alert=True)
        return False
    if not is_allowed_user(user_id):
        await callback.answer("\u0414\u043e\u0441\u0442\u0443\u043f \u0437\u0430\u043f\u0440\u0435\u0449\u0435\u043d", show_alert=True)
        return False
    return True


@router.message(Command("add_mail"))
@router.message(F.text == ADD_MAIL_LABEL)
async def add_mailbox_start(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.clear()
    await state.set_state(AddMailboxState.title)
    await message.answer(
        "\u0412\u0432\u0435\u0434\u0438 \u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u0435\u0435 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043f\u043e\u0447\u0442\u044b. \u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: \u041e\u0441\u043d\u043e\u0432\u043d\u0430\u044f \u043f\u043e\u0447\u0442\u0430 \u0430\u0440\u0435\u043d\u0434\u044b",
        reply_markup=main_menu_keyboard(),
    )


@router.message(AddMailboxState.title)
async def add_mailbox_title(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AddMailboxState.email)
    await message.answer("\u0412\u0432\u0435\u0434\u0438 email \u044f\u0449\u0438\u043a\u0430 Outlook/Hotmail", reply_markup=main_menu_keyboard())


@router.message(AddMailboxState.email)
async def add_mailbox_email(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(email=(message.text or "").strip())
    await state.set_state(AddMailboxState.password)
    await message.answer("\u0412\u0432\u0435\u0434\u0438 \u043f\u0430\u0440\u043e\u043b\u044c \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f \u0438\u043b\u0438 IMAP-\u043f\u0430\u0440\u043e\u043b\u044c", reply_markup=main_menu_keyboard())


@router.message(AddMailboxState.password)
async def add_mailbox_password(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(password=(message.text or "").strip())
    await state.set_state(AddMailboxState.imap_host)
    await message.answer(
        "\u0412\u0432\u0435\u0434\u0438 IMAP host. \u0414\u043b\u044f Outlook \u043e\u0431\u044b\u0447\u043d\u043e: imap-mail.outlook.com",
        reply_markup=main_menu_keyboard(),
    )


@router.message(AddMailboxState.imap_host)
async def add_mailbox_imap_host(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    value = ((message.text or "").strip() or "imap-mail.outlook.com")
    await state.update_data(imap_host=value)
    await state.set_state(AddMailboxState.imap_port)
    await message.answer("\u0412\u0432\u0435\u0434\u0438 IMAP port. \u041e\u0431\u044b\u0447\u043d\u043e: 993", reply_markup=main_menu_keyboard())


@router.message(AddMailboxState.imap_port)
async def add_mailbox_imap_port(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("\u041f\u043e\u0440\u0442 \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u0442\u044c \u0447\u0438\u0441\u043b\u043e\u043c. \u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: 993", reply_markup=main_menu_keyboard())
        return

    await state.update_data(imap_port=int(text))
    await state.set_state(AddMailboxState.account_name)
    await message.answer(
        "\u0412\u0432\u0435\u0434\u0438 \u0438\u043c\u044f \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u0430, \u043a\u043e\u0442\u043e\u0440\u043e\u0435 \u0431\u0443\u0434\u0435\u0442 \u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0430\u0442\u044c\u0441\u044f \u0432 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0438.\n"
        "\u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: Rent #1 \u0438\u043b\u0438 \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0430\u043a\u043a\u0430\u0443\u043d\u0442",
        reply_markup=main_menu_keyboard(),
    )


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
            account_name=(message.text or "").strip(),
        )

    await state.clear()
    await message.answer(
        "\u041f\u043e\u0447\u0442\u0430 \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0430.\n\n" + _mailbox_summary(mailbox),
        reply_markup=mailbox_actions_keyboard(mailbox.id),
    )
    await send_main_menu(message, "\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e \u043e\u0442\u043a\u0440\u044b\u0442\u043e. \u041c\u043e\u0436\u0435\u0448\u044c \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0435\u0449\u0435 \u043e\u0434\u043d\u0443 \u043f\u043e\u0447\u0442\u0443 \u0438\u043b\u0438 \u043f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u0441\u043f\u0438\u0441\u043a\u0443.")


@router.message(Command("list_mail"))
@router.message(F.text == LIST_MAIL_LABEL)
async def list_mailboxes(message: Message) -> None:
    if not await ensure_access(message):
        return
    owner_telegram_id = _ensure_user_id(message)
    await _show_mailbox_list(message, owner_telegram_id)


@router.callback_query(F.data == "nav:home")
async def navigate_home(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    await state.clear()
    await callback.answer()
    await send_main_menu(callback)


@router.callback_query(F.data == "nav:list")
async def navigate_list(callback: CallbackQuery) -> None:
    if not await _ensure_callback_access(callback):
        return
    owner_telegram_id = _callback_user_id(callback)
    await callback.answer()
    await _show_mailbox_list(callback.message, owner_telegram_id)


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
        await callback.message.answer("\u041f\u043e\u0447\u0442\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0438\u043b\u0438 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    await callback.message.answer(_mailbox_summary(mailbox), reply_markup=mailbox_actions_keyboard(mailbox.id))
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
            await callback.message.answer("\u041f\u043e\u0447\u0442\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0438\u043b\u0438 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430.", reply_markup=main_menu_keyboard())
            await callback.answer()
            return
        mailbox = await repo.toggle_active(mailbox)

    await callback.message.answer(_mailbox_summary(mailbox), reply_markup=mailbox_actions_keyboard(mailbox.id))
    await callback.answer("\u0421\u0442\u0430\u0442\u0443\u0441 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d")


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
            await callback.message.answer("\u041f\u043e\u0447\u0442\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0438\u043b\u0438 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430.", reply_markup=main_menu_keyboard())
            await callback.answer()
            return
        title = mailbox.title
        await repo.delete(mailbox)

    await callback.message.answer(f"\u041f\u043e\u0447\u0442\u0430 {title} \u0443\u0434\u0430\u043b\u0435\u043d\u0430.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title:"))
async def edit_mailbox_title_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    await state.set_state(EditMailboxState.title)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.answer("\u0412\u0432\u0435\u0434\u0438 \u043d\u043e\u0432\u043e\u0435 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043f\u043e\u0447\u0442\u044b", reply_markup=main_menu_keyboard())
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
            await message.answer("\u041f\u043e\u0447\u0442\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0438\u043b\u0438 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430.", reply_markup=main_menu_keyboard())
            await state.clear()
            return
        mailbox = await repo.update_title(mailbox, (message.text or "").strip())

    await state.clear()
    await message.answer(_mailbox_summary(mailbox), reply_markup=mailbox_actions_keyboard(mailbox.id))


@router.callback_query(F.data.startswith("edit_account:"))
async def edit_mailbox_account_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    await state.set_state(EditMailboxState.account_name)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.answer("\u0412\u0432\u0435\u0434\u0438 \u043d\u043e\u0432\u043e\u0435 \u0438\u043c\u044f \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u0430", reply_markup=main_menu_keyboard())
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
            await message.answer("\u041f\u043e\u0447\u0442\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0438\u043b\u0438 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430.", reply_markup=main_menu_keyboard())
            await state.clear()
            return
        mailbox = await repo.update_account_name(mailbox, (message.text or "").strip())

    await state.clear()
    await message.answer(_mailbox_summary(mailbox), reply_markup=mailbox_actions_keyboard(mailbox.id))


@router.callback_query(F.data.startswith("edit_password:"))
async def edit_mailbox_password_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    await state.set_state(EditMailboxState.password)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.answer("\u0412\u0432\u0435\u0434\u0438 \u043d\u043e\u0432\u044b\u0439 \u043f\u0430\u0440\u043e\u043b\u044c \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f / IMAP-\u043f\u0430\u0440\u043e\u043b\u044c", reply_markup=main_menu_keyboard())
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
            await message.answer("\u041f\u043e\u0447\u0442\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430 \u0438\u043b\u0438 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430.", reply_markup=main_menu_keyboard())
            await state.clear()
            return
        mailbox = await repo.update_password(mailbox, (message.text or "").strip())

    await state.clear()
    await message.answer("\u041f\u0430\u0440\u043e\u043b\u044c \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d.", reply_markup=mailbox_actions_keyboard(mailbox.id))
