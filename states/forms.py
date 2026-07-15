from aiogram.fsm.state import State, StatesGroup


class AddHolding(StatesGroup):
    choosing_type = State()
    entering_ticker = State()
    entering_quantity = State()
