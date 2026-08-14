from aiogram.fsm.state import StatesGroup, State

class RepliesStates(StatesGroup):
    waiting_for_pain_selection = State()
    waiting_for_new_pain_name = State()
    waiting_for_note_text = State()
