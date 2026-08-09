from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StudentRegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_patronymic = State()
