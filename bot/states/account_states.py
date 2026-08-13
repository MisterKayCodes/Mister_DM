from aiogram.fsm.state import StatesGroup, State

class AddAccountStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_session_string = State()
    waiting_for_delay_min = State()
    waiting_for_delay_max = State()
    waiting_for_session_retry = State()
