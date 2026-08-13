from aiogram.fsm.state import StatesGroup, State

class AddTemplateStates(StatesGroup):
    waiting_for_content = State()
