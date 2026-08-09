from __future__ import annotations

import re
import string
from dataclasses import dataclass
from typing import Protocol


class VocabularyItemLike(Protocol):
    word: str
    definition: str
    accepted_answers: list[str]
    keywords: list[str]


@dataclass(frozen=True)
class EvaluationResult:
    is_correct: bool
    reason: str
    matched_keywords: tuple[str, ...] = ()


class AnswerEvaluator(Protocol):
    def evaluate(
        self, user_answer: str, vocabulary_item: VocabularyItemLike
    ) -> EvaluationResult: ...


_PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation.replace("'", ""))


def normalize_answer(value: str) -> str:
    normalized = value.lower().strip()
    normalized = normalized.translate(_PUNCTUATION_TABLE)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


class RuleBasedEvaluator:
    def __init__(self, keyword_threshold: float = 0.6) -> None:
        self.keyword_threshold = keyword_threshold

    def evaluate(self, user_answer: str, vocabulary_item: VocabularyItemLike) -> EvaluationResult:
        normalized_answer = normalize_answer(user_answer)
        accepted_answers = vocabulary_item.accepted_answers or [vocabulary_item.definition]

        for accepted_answer in accepted_answers:
            if normalized_answer == normalize_answer(accepted_answer):
                return EvaluationResult(is_correct=True, reason="exact_match")

        keywords = [
            normalize_answer(keyword) for keyword in vocabulary_item.keywords if keyword.strip()
        ]
        if keywords:
            matched = tuple(keyword for keyword in keywords if keyword in normalized_answer)
            required_count = max(1, round(len(keywords) * self.keyword_threshold))
            if len(matched) >= required_count:
                return EvaluationResult(
                    is_correct=True, reason="keyword_match", matched_keywords=matched
                )

        return EvaluationResult(is_correct=False, reason="no_match")
