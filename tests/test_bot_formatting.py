from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.bot.formatting import (
    answer_feedback,
    error_text,
    format_student_result,
    question_text,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _question(question_number: int = 3, total: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        deadline=_now() + timedelta(seconds=30),
        question_number=question_number,
        vocabulary_item=SimpleNamespace(
            word="predator", definition="an animal that hunts other animals"
        ),
    )


def _attempt(answered: list[bool], total: int = 5) -> SimpleNamespace:
    questions = []
    for index, is_correct in enumerate(answered, start=1):
        questions.append(
            SimpleNamespace(
                question_number=index,
                answered_at=_now(),
                is_correct=is_correct,
                is_expired=False,
            )
        )
    return SimpleNamespace(total_questions=total, questions=questions)


def _outcome(
    *,
    is_correct: bool,
    is_expired: bool = False,
    next_question: object = None,
    user_answer: str | None = "animal that hunts",
) -> SimpleNamespace:
    attempt = _attempt([True, is_correct and not is_expired])
    question = _question()
    question.check_attempt = attempt
    question.user_answer = user_answer
    return SimpleNamespace(
        question=question,
        is_correct=is_correct,
        is_expired=is_expired,
        next_question=next_question,
    )


def test_question_text_contains_word_and_countdown() -> None:
    text = question_text(_question(), 5)
    assert "Question 3/5" in text
    assert "predator" in text
    assert "Time remaining" in text


def test_correct_feedback_shows_score() -> None:
    text = answer_feedback(_outcome(is_correct=True, next_question=object()))
    assert "Correct!" in text
    assert "Your answer" in text
    assert "animal that hunts" in text
    assert "Score: 2/5" in text
    assert "Next word" in text


def test_incorrect_feedback_shows_correct_answer() -> None:
    text = answer_feedback(_outcome(is_correct=False))
    assert "Incorrect" in text
    assert "animal that hunts other animals" in text
    assert "Score: 1/5" in text


def test_expired_feedback_shows_correct_answer_without_user_answer() -> None:
    text = answer_feedback(_outcome(is_correct=False, is_expired=True, user_answer=None))
    assert "Time's up" in text
    assert "animal that hunts other animals" in text
    assert "Your answer" not in text


def test_escapes_html_in_user_generated_content() -> None:
    question = _question()
    question.vocabulary_item = SimpleNamespace(word="<predator>", definition="an animal & a plant")
    question.check_attempt = _attempt([True, False])
    question.user_answer = "a <big> cat"
    outcome = SimpleNamespace(
        question=question,
        is_correct=False,
        is_expired=False,
        next_question=None,
    )
    text = answer_feedback(outcome)
    assert "<predator>" not in text
    assert "&lt;predator&gt;" in text
    assert "&amp;" in text
    assert "a <big> cat" not in text
    assert "a &lt;big&gt; cat" in text


def test_format_student_result_contains_score_and_grade() -> None:
    result = SimpleNamespace(
        score=4,
        total_questions=5,
        percentage=80.0,
        correct_answers=4,
        incorrect_answers=1,
        expired_answers=0,
        words_to_review=["habitat"],
    )
    text = format_student_result(result)
    assert "4/5" in text
    assert "80%" in text
    assert "Good" in text
    assert "habitat" in text


def test_error_text_prepends_icon() -> None:
    assert error_text("Something went wrong") == "⚠️ Something went wrong"
