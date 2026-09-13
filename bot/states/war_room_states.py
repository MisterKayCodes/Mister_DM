from aiogram.fsm.state import State, StatesGroup

class WarRoomStates(StatesGroup):
    waiting_for_override_text = State()
