from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.timer import is_answer_expired


def test_answer_before_deadline() -> None:
    deadline = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    assert not is_answer_expired(deadline - timedelta(seconds=1), deadline)


def test_answer_exactly_at_deadline() -> None:
    deadline = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    assert not is_answer_expired(deadline, deadline)


def test_answer_after_deadline() -> None:
    deadline = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    assert is_answer_expired(deadline + timedelta(microseconds=1), deadline)
