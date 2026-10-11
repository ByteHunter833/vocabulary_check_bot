from __future__ import annotations

from types import SimpleNamespace

from app.services.checking_service import select_attempt_vocabulary_items


def _items(count: int) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(id=index, position=index, word=f"word-{index}")
        for index in range(1, count + 1)
    ]


def test_selects_50_random_items_from_100() -> None:
    selected = select_attempt_vocabulary_items(_items(100), attempt_id=1, limit=50)

    assert len(selected) == 50
    assert len({item.id for item in selected}) == 50


def test_selection_is_stable_for_attempt() -> None:
    first = select_attempt_vocabulary_items(_items(100), attempt_id=25, limit=50)
    second = select_attempt_vocabulary_items(_items(100), attempt_id=25, limit=50)

    assert [item.id for item in first] == [item.id for item in second]


def test_selection_differs_between_attempts() -> None:
    first = select_attempt_vocabulary_items(_items(100), attempt_id=25, limit=50)
    second = select_attempt_vocabulary_items(_items(100), attempt_id=26, limit=50)

    assert [item.id for item in first] != [item.id for item in second]


def test_selection_uses_all_items_when_less_than_limit() -> None:
    selected = select_attempt_vocabulary_items(_items(10), attempt_id=1, limit=50)

    assert [item.id for item in selected] == list(range(1, 11))
