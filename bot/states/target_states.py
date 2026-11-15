from aiogram.fsm.state import StatesGroup, State


class AddTargetStates(StatesGroup):
    waiting_for_text_paste = State()
    waiting_for_file_upload = State()
    waiting_for_scout_link = State()
    waiting_for_scout_depth = State()
