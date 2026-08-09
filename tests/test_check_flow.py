from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.answer_evaluator import RuleBasedEvaluator
from app.services.grading import calculate_percentage
from app.services.timer import is_answer_expired


class SimpleCheckFlow:
    def __init__(self, items: list[dict[str, object]], time_limit_seconds: int = 60) -> None:
        self.items = items
        self.time_limit_seconds = time_limit_seconds
        self.index = -1
        self.current_started_at: datetime | None = None
        self.current_deadline: datetime | None = None
        self.correct = 0
        self.incorrect = 0
        self.expired = 0
        self.finished = False
        self.evaluator = RuleBasedEvaluator()

    def start(self, now: datetime) -> dict[str, object]:
        self.index = 0
        self.current_started_at = now
        self.current_deadline = now + timedelta(seconds=self.time_limit_seconds)
        return self.items[self.index]

    def answer(self, answer: str, now: datetime) -> dict[str, object] | None:
        assert self.current_deadline is not None
        item = type("Item", (), self.items[self.index])
        if is_answer_expired(now, self.current_deadline):
            self.expired += 1
        elif self.evaluator.evaluate(answer, item).is_correct:
            self.correct += 1
        else:
            self.incorrect += 1

        self.index += 1
        if self.index >= len(self.items):
            self.finished = True
            return None
        self.current_started_at = now
        self.current_deadline = now + timedelta(seconds=self.time_limit_seconds)
        return self.items[self.index]

    @property
    def percentage(self) -> float:
        return calculate_percentage(self.correct, len(self.items))


def test_check_flow_start_answer_timeout_finish() -> None:
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    flow = SimpleCheckFlow(
        [
            {
                "word": "predator",
                "definition": "an animal that hunts other animals",
                "accepted_answers": ["an animal that hunts other animals"],
                "keywords": ["animal", "hunt"],
            },
            {
                "word": "habitat",
                "definition": "the natural home of an animal or plant",
                "accepted_answers": ["the natural home of an animal or plant"],
                "keywords": ["natural", "home"],
            },
        ]
    )

    first = flow.start(now)
    assert first["word"] == "predator"

    second = flow.answer("animal that hunts", now + timedelta(seconds=10))
    assert second is not None
    assert second["word"] == "habitat"
    assert flow.correct == 1

    finished = flow.answer("too late", now + timedelta(seconds=80))
    assert finished is None
    assert flow.finished
    assert flow.expired == 1
    assert flow.percentage == 50
