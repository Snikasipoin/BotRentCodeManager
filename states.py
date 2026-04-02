from aiogram.fsm.state import State, StatesGroup


class AddMailboxState(StatesGroup):
    title = State()
    email = State()
    password = State()
    imap_host = State()
    imap_port = State()
    account_name = State()


class EditMailboxState(StatesGroup):
    title = State()
    account_name = State()
    password = State()
