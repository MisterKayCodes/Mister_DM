from aiogram.fsm.state import StatesGroup, State

class SafetyStates(StatesGroup):
    waiting_for_daily_cap = State()
