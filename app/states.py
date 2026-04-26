from aiogram.fsm.state import State, StatesGroup


class AppSG(StatesGroup):
    main = State()
    support_category = State()
