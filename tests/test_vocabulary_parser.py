from __future__ import annotations

import pytest

from app.services.vocabulary_service import VocabularyParseError, parse_vocabulary_text


def test_parse_vocabulary_text() -> None:
    items = parse_vocabulary_text(
        "predator - an animal that hunts other animals\n"
        "habitat - the natural home of an animal or plant"
    )
    assert len(items) == 2
    assert items[0].word == "predator"
    assert items[0].definition == "an animal that hunts other animals"
    assert "animal" in items[0].keywords


def test_parse_invalid_line() -> None:
    with pytest.raises(VocabularyParseError):
        parse_vocabulary_text("predator")
