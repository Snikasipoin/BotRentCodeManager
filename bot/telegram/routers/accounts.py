from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import Account
from bot.telegram.keyboards.main import ACCOUNTS, account_actions, account_edit_actions, accounts_list_keyboard, main_menu
from bot.telegram.states.account import AccountEditForm, AccountForm
from bot.utils.encryption import Cipher

router = Router()
_cipher = Cipher()


def _format_account(account: Account) -> str:
    return (
        f"📋 Аккаунт #{account.id}\n"
        f"Название: {account.title}\n"
        f"Steam: {account.steam_login}\n"
        f"Faceit: {account.faceit_login or '-'}\n"
        f"Email: {account.email}\n"
        f"IMAP: {account.email_imap_host}:{account.email_imap_port}\n"
        f"Статус: {account.status.value}\n"
        f"Заметки: {account.notes or '-'}"
    )


async def _list_accounts(message: Message | CallbackQuery, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        accounts = (await session.scalars(select(Account).order_by(Account.id.asc()))).all()
    items = [(account.id, account.title, account.status.value) for account in accounts]
    target = message.message if isinstance(message, CallbackQuery) else message
    if not items:
        await target.answer("Аккаунтов пока нет. Добавь первый аккаунт.", reply_markup=accounts_list_keyboard(items))
        return
    await target.answer("📋 Список аккаунтов", reply_markup=accounts_list_keyboard(items))


@router.message(Command("accounts"))
@router.message(F.text == ACCOUNTS)
async def accounts_menu(message: Message, session_factory: async_sessionmaker[AsyncSession]) -> None:
    await _list_accounts(message, session_factory)


@router.callback_query(F.data == "account:list")
async def accounts_list_callback(callback: CallbackQuery, session_factory: async_sessionmaker[AsyncSession]) -> None:
    await callback.answer()
    await _list_accounts(callback, session_factory)


@router.callback_query(F.data == "account:add")
async def account_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AccountForm.title)
    await callback.answer()
    await callback.message.answer("Введи название аккаунта")


@router.message(AccountForm.title)
async def account_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AccountForm.steam_login)
    await message.answer("Введите Steam login")


@router.message(AccountForm.steam_login)
async def account_steam_login(message: Message, state: FSMContext) -> None:
    await state.update_data(steam_login=message.text.strip())
    await state.set_state(AccountForm.steam_password)
    await message.answer("Введите Steam password")


@router.message(AccountForm.steam_password)
async def account_steam_password(message: Message, state: FSMContext) -> None:
    await state.update_data(steam_password=message.text.strip())
    await state.set_state(AccountForm.faceit_login)
    await message.answer("Введите Faceit login или '-' если его нет")


@router.message(AccountForm.faceit_login)
async def account_faceit_login(message: Message, state: FSMContext) -> None:
    value = message.text.strip()
    await state.update_data(faceit_login=None if value == "-" else value)
    await state.set_state(AccountForm.faceit_password)
    await message.answer("Введите Faceit password или '-' если его нет")


@router.message(AccountForm.faceit_password)
async def account_faceit_password(message: Message, state: FSMContext) -> None:
    value = message.text.strip()
    await state.update_data(faceit_password=None if value == "-" else value)
    await state.set_state(AccountForm.email)
    await message.answer("Введите email аккаунта")


@router.message(AccountForm.email)
async def account_email(message: Message, state: FSMContext) -> None:
    await state.update_data(email=message.text.strip())
    await state.set_state(AccountForm.email_password)
    await message.answer("Введите пароль от email / app password")


@router.message(AccountForm.email_password)
async def account_email_password(message: Message, state: FSMContext) -> None:
    await state.update_data(email_password=message.text.strip())
    await state.set_state(AccountForm.email_imap_host)
    await message.answer("Введите IMAP host (обычно imap-mail.outlook.com)")


@router.message(AccountForm.email_imap_host)
async def account_email_imap_host(message: Message, state: FSMContext) -> None:
    await state.update_data(email_imap_host=message.text.strip() or "imap-mail.outlook.com")
    await state.set_state(AccountForm.email_imap_port)
    await message.answer("Введите IMAP port (обычно 993)")


@router.message(AccountForm.email_imap_port)
async def account_email_imap_port(message: Message, state: FSMContext) -> None:
    await state.update_data(email_imap_port=int(message.text.strip()))
    await state.set_state(AccountForm.notes)
    await message.answer("Введите заметки или '-' если их нет")


@router.message(AccountForm.notes)
async def account_finish(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]) -> None:
    data = await state.get_data()
    notes = message.text.strip()
    async with session_factory() as session:
        account = Account(
            title=data['title'],
            steam_login=data['steam_login'],
            steam_password_encrypted=_cipher.encrypt(data['steam_password']) or "",
            faceit_login=data['faceit_login'],
            faceit_password_encrypted=_cipher.encrypt(data['faceit_password']),
            email=data['email'],
            email_password_encrypted=_cipher.encrypt(data['email_password']) or "",
            email_imap_host=data['email_imap_host'],
            email_imap_port=data['email_imap_port'],
            notes=None if notes == '-' else notes,
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)
    await state.clear()
    await message.answer("Аккаунт сохранён.", reply_markup=main_menu())
    await message.answer(_format_account(account), reply_markup=account_actions(account.id))


@router.callback_query(F.data.startswith("account:view:"))
async def account_view(callback: CallbackQuery, session_factory: async_sessionmaker[AsyncSession]) -> None:
    account_id = int(callback.data.split(":")[-1])
    async with session_factory() as session:
        account = await session.get(Account, account_id)
    await callback.answer()
    if not account:
        await callback.message.answer("Аккаунт не найден")
        return
    await callback.message.answer(_format_account(account), reply_markup=account_actions(account.id))


@router.callback_query(F.data.startswith("account:editmenu:"))
async def account_edit_menu(callback: CallbackQuery) -> None:
    account_id = int(callback.data.split(":")[-1])
    await callback.answer()
    await callback.message.answer("Выбери поле для редактирования", reply_markup=account_edit_actions(account_id))


@router.callback_query(F.data.startswith("account:edit:"))
async def account_edit(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, account_id, field = callback.data.split(":", 3)
    await state.set_state(AccountEditForm.value)
    await state.update_data(account_id=int(account_id), field=field)
    await callback.answer()
    prompts = {
        "title": "Введи новое название аккаунта",
        "steam_login": "Введи новый Steam login",
        "steam_password": "Введи новый Steam password",
        "faceit_login": "Введи новый Faceit login или '-' чтобы очистить",
        "faceit_password": "Введи новый Faceit password или '-' чтобы очистить",
        "email": "Введи новый email",
        "email_password": "Введи новый email password / app password",
        "email_imap_host": "Введи новый IMAP host",
        "email_imap_port": "Введи новый IMAP port",
        "notes": "Введи новые заметки или '-' чтобы очистить",
    }
    await callback.message.answer(prompts.get(field, "Введи новое значение"))


@router.message(AccountEditForm.value)
async def account_edit_value(message: Message, state: FSMContext, session_factory: async_sessionmaker[AsyncSession]) -> None:
    data = await state.get_data()
    account_id = int(data["account_id"])
    field = str(data["field"])
    value = message.text.strip()
    async with session_factory() as session:
        account = await session.get(Account, account_id)
        if not account:
            await state.clear()
            await message.answer("Аккаунт не найден", reply_markup=main_menu())
            return
        if field == "title":
            account.title = value
        elif field == "steam_login":
            account.steam_login = value
        elif field == "steam_password":
            account.steam_password_encrypted = _cipher.encrypt(value) or ""
        elif field == "faceit_login":
            account.faceit_login = None if value == "-" else value
        elif field == "faceit_password":
            account.faceit_password_encrypted = None if value == "-" else _cipher.encrypt(value)
        elif field == "email":
            account.email = value
        elif field == "email_password":
            account.email_password_encrypted = _cipher.encrypt(value) or ""
        elif field == "email_imap_host":
            account.email_imap_host = value
        elif field == "email_imap_port":
            account.email_imap_port = int(value)
        elif field == "notes":
            account.notes = None if value == "-" else value
        await session.commit()
        await session.refresh(account)
    await state.clear()
    await message.answer("Аккаунт обновлён.", reply_markup=main_menu())
    await message.answer(_format_account(account), reply_markup=account_actions(account.id))


@router.callback_query(F.data.startswith("account:delete:"))
async def account_delete(callback: CallbackQuery, session_factory: async_sessionmaker[AsyncSession]) -> None:
    account_id = int(callback.data.split(":")[-1])
    async with session_factory() as session:
        account = await session.get(Account, account_id)
        if account:
            await session.delete(account)
            await session.commit()
    await callback.answer("Удалено")
    await callback.message.answer("Аккаунт удалён.", reply_markup=main_menu())


