from __future__ import annotations

from dataclasses import dataclass

from app.services.answer_evaluator import RuleBasedEvaluator


@dataclass
class Item:
    word: str = "predator"
    definition: str = "an animal that hunts other animals"
    accepted_answers: list[str] | None = None
    keywords: list[str] | None = None

    def __post_init__(self) -> None:
        if self.accepted_answers is None:
            self.accepted_answers = [self.definition]
        if self.keywords is None:
            self.keywords = ["animal", "hunt"]


def test_exact_answer() -> None:
    result = RuleBasedEvaluator().evaluate("an animal that hunts other animals", Item())
    assert result.is_correct
    assert result.reason == "exact_match"


def test_case_differences() -> None:
    assert RuleBasedEvaluator().evaluate("AN ANIMAL THAT HUNTS OTHER ANIMALS", Item()).is_correct


def test_extra_whitespace() -> None:
    assert (
        RuleBasedEvaluator().evaluate("  an   animal that hunts other animals  ", Item()).is_correct
    )


def test_punctuation() -> None:
    assert RuleBasedEvaluator().evaluate("an animal that hunts other animals.", Item()).is_correct


def test_accepted_answers() -> None:
    item = Item(accepted_answers=["hunter animal"], keywords=["hunter"])
    assert RuleBasedEvaluator().evaluate("hunter animal", item).is_correct


def test_keyword_matching() -> None:
    assert RuleBasedEvaluator().evaluate("It is an animal that can hunt prey", Item()).is_correct


def test_incorrect_answer() -> None:
    assert not RuleBasedEvaluator().evaluate("a place where people live", Item()).is_correct
