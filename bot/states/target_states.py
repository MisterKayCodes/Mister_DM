from aiogram.fsm.state import StatesGroup, State


class AddTargetStates(StatesGroup):
    # Two states only — not three.
    # The moment the user taps "📝 Paste Usernames" or "📁 Upload TXT File",
    # we already know their intent. A "waiting_for_input_method" middle-state
    # would add complexity with zero value. The keyboard button IS the state transition.
    waiting_for_text_paste = State()
    waiting_for_file_upload = State()
