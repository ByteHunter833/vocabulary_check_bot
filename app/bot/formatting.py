from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from app.services.grading import grade_label

QUESTION_ICON = "❓"
CORRECT_ICON = "✅"
INCORRECT_ICON = "❌"
EXPIRED_ICON = "⏰"
TROPHY_ICON = "🏆"
ERROR_ICON = "⚠️"
ARROW_ICON = "⏬"
CLOCK_ICON = "⏳"

_MAX_ANSWER_LENGTH = 200


def _esc(value: object) -> str:
    return escape(str(value))


def _truncate(text: str, limit: int = _MAX_ANSWER_LENGTH) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def question_text(question, total: int) -> str:
    remaining_seconds = max(0, int((question.deadline - datetime.now(UTC)).total_seconds()))
    word = _esc(question.vocabulary_item.word)
    return (
        f"{QUESTION_ICON} <b>Question {question.question_number}/{total}</b>\n\n"
        f"What does <i>{word}</i> mean?\n\n"
        f"{CLOCK_ICON} Time remaining: {remaining_seconds}s"
    )


def answer_feedback(outcome) -> str:
    word = _esc(outcome.question.vocabulary_item.word)
    definition = _esc(outcome.question.vocabulary_item.definition)
    total = outcome.question.check_attempt.total_questions
    score = _running_score(outcome.question.check_attempt)

    if outcome.is_expired:
        lines = [
            f"{EXPIRED_ICON} <b>Time's up!</b>",
            "",
            f"Correct answer: <b>{word}</b> — {definition}",
        ]
    elif outcome.is_correct:
        user_answer = _truncate(_esc(outcome.question.user_answer or ""))
        lines = [
            f"{CORRECT_ICON} <b>Correct!</b>",
            "",
            f"Your answer: {user_answer}",
        ]
    else:
        user_answer = _truncate(_esc(outcome.question.user_answer or ""))
        lines = [
            f"{INCORRECT_ICON} <b>Incorrect.</b>",
            "",
            f"Your answer: {user_answer}",
            f"Correct answer: <b>{word}</b> — {definition}",
        ]

    lines.extend(["", f"{TROPHY_ICON} Score: {score}/{total}"])

    if outcome.next_question is not None:
        lines.extend(["", f"Next word... {ARROW_ICON}"])

    return "\n".join(lines)


def _running_score(attempt) -> int:
    if attempt is None or attempt.questions is None:
        return 0
    return sum(
        1
        for question in attempt.questions
        if question.answered_at is not None
        and question.is_correct is True
        and not question.is_expired
    )


def error_text(message: str) -> str:
    return f"{ERROR_ICON} {message}"


def format_student_result(result) -> str:
    review_words = "\n".join(f"- {_esc(word)}" for word in result.words_to_review) or "None"
    return (
        "🎓 <b>Vocabulary Check Complete!</b>\n\n"
        f"{TROPHY_ICON} Score: <b>{result.score}/{result.total_questions}</b>\n"
        f"📊 Grade: <b>{round(result.percentage)}%</b> "
        f"({_esc(grade_label(result.percentage))})\n\n"
        f"{CORRECT_ICON} Correct: {result.correct_answers}\n"
        f"{INCORRECT_ICON} Incorrect: {result.incorrect_answers}\n"
        f"{EXPIRED_ICON} Time expired: {result.expired_answers}\n\n"
        "📚 <b>Words to review:</b>\n"
        f"{review_words}"
    )
