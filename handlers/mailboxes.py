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
    status = "активна" if mailbox.is_active else "выключена"
    return (
        f"Почта: {mailbox.title}\n"
        f"Email: {mailbox.email}\n"
        f"Аккаунт: {mailbox.account_name}\n"
        f"Проверка кодов: Steam + FACEIT автоматически\n"
        f"Статус: {status}"
    )


async def _show_mailbox_list(message: Message, owner_telegram_id: int) -> None:
    async with SessionLocal() as session:
        repo = MailboxRepository(session)
        mailboxes = await repo.list_by_owner(owner_telegram_id)

    if not mailboxes:
        await message.answer(
            "Список почт пуст. Нажми «Добавить почту», чтобы начать.",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = []
    for mailbox in mailboxes:
        status = "активна" if mailbox.is_active else "выключена"
        lines.append(f"{mailbox.id}. {mailbox.title} | {mailbox.email} | {mailbox.account_name} | {status}")

    await message.answer(
        "Сохраненные почты:\n\n" + "\n".join(lines),
        reply_markup=mailbox_list_keyboard(mailboxes),
    )


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
@router.message(F.text == ADD_MAIL_LABEL)
async def add_mailbox_start(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.clear()
    await state.set_state(AddMailboxState.title)
    await message.answer(
        "Введи внутреннее название почты. Например: Основная почта аренды",
        reply_markup=main_menu_keyboard(),
    )


@router.message(AddMailboxState.title)
async def add_mailbox_title(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AddMailboxState.email)
    await message.answer("Введи email ящика Outlook/Hotmail", reply_markup=main_menu_keyboard())


@router.message(AddMailboxState.email)
async def add_mailbox_email(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(email=(message.text or "").strip())
    await state.set_state(AddMailboxState.password)
    await message.answer("Введи пароль приложения или IMAP-пароль", reply_markup=main_menu_keyboard())


@router.message(AddMailboxState.password)
async def add_mailbox_password(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    await state.update_data(password=(message.text or "").strip())
    await state.set_state(AddMailboxState.imap_host)
    await message.answer(
        "Введи IMAP host. Для Outlook обычно: imap-mail.outlook.com",
        reply_markup=main_menu_keyboard(),
    )


@router.message(AddMailboxState.imap_host)
async def add_mailbox_imap_host(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    value = ((message.text or "").strip() or "imap-mail.outlook.com")
    await state.update_data(imap_host=value)
    await state.set_state(AddMailboxState.imap_port)
    await message.answer("Введи IMAP port. Обычно: 993", reply_markup=main_menu_keyboard())


@router.message(AddMailboxState.imap_port)
async def add_mailbox_imap_port(message: Message, state: FSMContext) -> None:
    if not await ensure_access(message):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Порт должен быть числом. Например: 993", reply_markup=main_menu_keyboard())
        return

    await state.update_data(imap_port=int(text))
    await state.set_state(AddMailboxState.account_name)
    await message.answer(
        "Введи имя аккаунта, которое будет отображаться в уведомлении.\n"
        "Например: Rent #1 или Основной аккаунт",
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
        "Почта успешно добавлена.\n\n" + _mailbox_summary(mailbox),
        reply_markup=mailbox_actions_keyboard(mailbox.id),
    )
    await send_main_menu(message, "Главное меню открыто. Можешь добавить еще одну почту или перейти к списку.")


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
    fake_message = callback.message
    await _show_mailbox_list(fake_message, owner_telegram_id)


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
        await callback.message.answer("Почта не найдена или недоступна.", reply_markup=main_menu_keyboard())
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
            await callback.message.answer("Почта не найдена или недоступна.", reply_markup=main_menu_keyboard())
            await callback.answer()
            return
        mailbox = await repo.toggle_active(mailbox)

    await callback.message.answer(_mailbox_summary(mailbox), reply_markup=mailbox_actions_keyboard(mailbox.id))
    await callback.answer("Статус обновлен")


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
            await callback.message.answer("Почта не найдена или недоступна.", reply_markup=main_menu_keyboard())
            await callback.answer()
            return
        title = mailbox.title
        await repo.delete(mailbox)

    await callback.message.answer(f"Почта {title} удалена.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title:"))
async def edit_mailbox_title_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_callback_access(callback):
        return
    mailbox_id = int(callback.data.split(":")[1])
    await state.set_state(EditMailboxState.title)
    await state.update_data(mailbox_id=mailbox_id)
    await callback.message.answer("Введи новое название почты", reply_markup=main_menu_keyboard())
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
            await message.answer("Почта не найдена или недоступна.", reply_markup=main_menu_keyboard())
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
    await callback.message.answer("Введи новое имя аккаунта", reply_markup=main_menu_keyboard())
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
            await message.answer("Почта не найдена или недоступна.", reply_markup=main_menu_keyboard())
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
    await callback.message.answer("Введи новый пароль приложения / IMAP-пароль", reply_markup=main_menu_keyboard())
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
            await message.answer("Почта не найдена или недоступна.", reply_markup=main_menu_keyboard())
            await state.clear()
            return
        mailbox = await repo.update_password(mailbox, (message.text or "").strip())

    await state.clear()
    await message.answer("Пароль обновлен.", reply_markup=mailbox_actions_keyboard(mailbox.id))
