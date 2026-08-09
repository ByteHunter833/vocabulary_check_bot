from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, VocabularyItem, VocabularyList, VocabularyStatus


class VocabularyParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedVocabularyItem:
    word: str
    definition: str
    accepted_answers: list[str]
    keywords: list[str]


_SEPARATORS = (" - ", " – ", " — ", ":", "=", "\t")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def extract_keywords(definition: str, *, max_keywords: int = 4) -> list[str]:
    words = re.findall(r"[a-zA-Z']+", definition.lower())
    keywords: list[str] = []
    for word in words:
        stemmed = word[:-1] if word.endswith("s") and len(word) > 4 else word
        if len(stemmed) < 4 or stemmed in _STOP_WORDS:
            continue
        if stemmed not in keywords:
            keywords.append(stemmed)
        if len(keywords) == max_keywords:
            break
    return keywords


def parse_vocabulary_text(text: str) -> list[ParsedVocabularyItem]:
    items: list[ParsedVocabularyItem] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        word = ""
        definition = ""
        for separator in _SEPARATORS:
            if separator in line:
                word, definition = line.split(separator, 1)
                break

        if not word or not definition:
            raise VocabularyParseError(
                f'Could not parse "{line}". Use one item per line, '
                "for example: predator - an animal that hunts."
            )

        clean_word = word.strip(" -–—:\t")
        clean_definition = definition.strip(" -–—:\t.")
        if not clean_word or not clean_definition:
            raise VocabularyParseError(
                f'Could not parse "{line}". Word and definition are required.'
            )

        items.append(
            ParsedVocabularyItem(
                word=clean_word,
                definition=clean_definition,
                accepted_answers=[clean_definition],
                keywords=extract_keywords(clean_definition),
            )
        )

    if not items:
        raise VocabularyParseError("No vocabulary items found.")
    return items


class VocabularyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_list(
        self,
        *,
        title: str,
        creator: User,
        parsed_items: list[ParsedVocabularyItem],
    ) -> VocabularyList:
        vocabulary_list = VocabularyList(
            title=title,
            created_by=creator.id,
            status=VocabularyStatus.DRAFT,
        )
        self.session.add(vocabulary_list)
        await self.session.flush()

        for index, item in enumerate(parsed_items, start=1):
            self.session.add(
                VocabularyItem(
                    vocabulary_list_id=vocabulary_list.id,
                    word=item.word,
                    definition=item.definition,
                    accepted_answers=item.accepted_answers,
                    keywords=item.keywords,
                    position=index,
                )
            )

        await self.session.commit()
        await self.session.refresh(vocabulary_list)
        return vocabulary_list

    async def publish_vocabulary_list(self, vocabulary_list: VocabularyList) -> None:
        vocabulary_list.status = VocabularyStatus.PUBLISHED
        vocabulary_list.published_at = datetime.now(UTC)
        await self.session.commit()
