from __future__ import annotations


def calculate_percentage(correct_answers: int, total_questions: int) -> float:
    if total_questions <= 0:
        return 0.0
    return round((correct_answers / total_questions) * 100, 2)


def grade_label(percentage: float) -> str:
    if percentage >= 90:
        return "Excellent"
    if percentage >= 80:
        return "Good"
    if percentage >= 70:
        return "Satisfactory"
    return "Needs Improvement"
