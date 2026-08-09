from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminVocabularyStates(StatesGroup):
    waiting_for_vocabulary = State()
    confirming_vocabulary = State()


class AdminManagementStates(StatesGroup):
    waiting_for_admin_telegram_id = State()
