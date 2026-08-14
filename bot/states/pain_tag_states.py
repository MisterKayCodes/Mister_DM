from aiogram.fsm.state import StatesGroup, State

class PainPointStates(StatesGroup):
    waiting_for_username_to_tag = State()
