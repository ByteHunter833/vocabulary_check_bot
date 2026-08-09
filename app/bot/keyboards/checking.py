from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def student_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Available Checks", callback_data="student_checks"
                )
            ],
            [InlineKeyboardButton(text="My Results", callback_data="student_my_results")],
        ]
    )


def skip_patronymic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Skip", callback_data="student_skip_patronymic")]
        ]
    )


def start_check_keyboard(check_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Start Checking", callback_data=f"student_start_check:{check_id}"
                )
            ]
        ]
    )


def checks_keyboard(checks) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=check.title[:48], callback_data=f"student_start_check:{check.id}"
            )
        ]
        for check in checks
    ]
    rows.append([InlineKeyboardButton(text="Back", callback_data="student_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
