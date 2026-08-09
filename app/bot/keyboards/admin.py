from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_vocabulary_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Preview", callback_data="admin_vocab_preview"),
                InlineKeyboardButton(text="Publish Check", callback_data="admin_vocab_publish"),
            ],
            [InlineKeyboardButton(text="Cancel", callback_data="admin_vocab_cancel")],
        ]
    )


def admin_results_keyboard(check_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Refresh Results", callback_data=f"admin_results:{check_id}"
                )
            ]
        ]
    )
