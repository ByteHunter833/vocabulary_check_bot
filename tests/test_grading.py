from __future__ import annotations

from app.services.grading import calculate_percentage, grade_label


def test_scoring_100_percent() -> None:
    assert calculate_percentage(10, 10) == 100
    assert grade_label(100) == "Excellent"


def test_scoring_80_percent() -> None:
    assert calculate_percentage(8, 10) == 80
    assert grade_label(80) == "Good"


def test_scoring_50_percent() -> None:
    assert calculate_percentage(5, 10) == 50
    assert grade_label(50) == "Needs Improvement"


def test_scoring_0_percent() -> None:
    assert calculate_percentage(0, 10) == 0
    assert grade_label(0) == "Needs Improvement"
