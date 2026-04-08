from aiogram.fsm.state import State, StatesGroup


class AccountForm(StatesGroup):
    title = State()
    steam_login = State()
    steam_password = State()
    faceit_login = State()
    faceit_password = State()
    email = State()
    email_password = State()
    email_imap_host = State()
    email_imap_port = State()
    notes = State()