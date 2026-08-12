from aiogram.fsm.state import StatesGroup, State

class AddCampaignStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_account = State()
