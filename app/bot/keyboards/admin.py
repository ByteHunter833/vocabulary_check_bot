from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu_keyboard(*, is_super_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Upload Vocabulary", callback_data="admin_new_check")],
        [InlineKeyboardButton(text="View Results", callback_data="admin_choose_results")],
    ]
    if is_super_admin:
        rows.append([InlineKeyboardButton(text="Add Admin", callback_data="super_add_admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
            ],
            [InlineKeyboardButton(text="Choose Check", callback_data="admin_choose_results")],
        ]
    )


def admin_checks_keyboard(checks) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{check.id}. {check.title}"[:60],
                callback_data=f"admin_results:{check.id}",
            )
        ]
        for check in checks
    ]
    rows.append([InlineKeyboardButton(text="Back", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_students_keyboard(results) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{student.display_name} - {round(student.percentage)}%",
                callback_data=f"admin_student_result:{student.attempt_id}",
            )
        ]
        for student in results.top_results
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="Refresh", callback_data=f"admin_results:{results.check_id}"
            )
        ]
    )
    rows.append([InlineKeyboardButton(text="Choose Check", callback_data="admin_choose_results")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
