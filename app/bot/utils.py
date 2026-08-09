from __future__ import annotations

from aiogram.types import User as TelegramUser

from app.models import User
from app.services.grading import grade_label
from app.services.result_service import display_name


def telegram_user_data(user: TelegramUser) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def format_student_result(result) -> str:
    review_words = "\n".join(f"- {word}" for word in result.words_to_review) or "None"
    return (
        "Vocabulary Check Complete!\n\n"
        "Your Result\n\n"
        f"Score: {result.score}/{result.total_questions}\n"
        f"Grade: {round(result.percentage)}% ({grade_label(result.percentage)})\n\n"
        f"Correct: {result.correct_answers}\n"
        f"Incorrect: {result.incorrect_answers}\n"
        f"Time expired: {result.expired_answers}\n\n"
        "Words to review:\n"
        f"{review_words}"
    )


def format_admin_results(results) -> str:
    top = "\n".join(
        f"{index}. {student.display_name} - {round(student.percentage)}%"
        for index, student in enumerate(results.top_results, start=1)
    )
    return (
        "Vocabulary Check Results\n\n"
        f"Check: {results.title}\n"
        f"Students: {results.students}\n\n"
        f"Average score: {round(results.average_score)}%\n\n"
        "Top results:\n"
        f"{top or 'No completed attempts yet.'}"
    )


def format_individual_admin_result(student_result) -> str:
    review_words = "\n".join(f"- {word}" for word in student_result.words_to_review) or "None"
    return (
        f"Student: {student_result.display_name}\n\n"
        f"Score: {student_result.score}/{student_result.total_questions}\n"
        f"Percentage: {round(student_result.percentage)}%\n\n"
        f"Correct:\n{student_result.correct_answers}\n\n"
        f"Incorrect:\n{student_result.incorrect_answers}\n\n"
        f"Time expired:\n{student_result.expired_answers}\n\n"
        "Words to review:\n"
        f"{review_words}"
    )


def format_user_role(user: User) -> str:
    return f"{display_name(user)} ({user.role.value})"
