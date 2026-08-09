from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminVocabularyStates(StatesGroup):
    waiting_for_vocabulary = State()
    confirming_vocabulary = State()
