"""
What each language does to its words, as data: one file per alphabet in this
folder. A word is read with the rules of the alphabet its letters are in, so
a map needs no language set, and a group may mix them, even in one message.

- letters: the ranges of the alphabet (hexadecimal code points, both included);
- prefixes: letters stuck to the start of a word ("و" in "وتفتيش"), and how many may go together;
- endings: what a word may end in and still be the same word ("ات" in "سالكات",
  "ado" in "controlado"); the longest one is taken off;
- question_marks and question_words: what makes a line a question.

Every text of a file is made plain as a message is (see recognition.text), so
it is written as people type it. A file is added for a new alphabet; nothing
here names a language.
"""
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from recognition.text import plain

FOLDER = Path(__file__).parent
# A word shorter than this is not made shorter: too many words would be the same
SHORTEST_STEM = 3


@dataclass(frozen=True)
class Language:
    name: str
    letters: tuple[tuple[int, int], ...]
    prefixes: frozenset[str]
    prefixes_together: int
    endings: tuple[str, ...]           # the longest first
    question_marks: tuple[str, ...]
    question_words: tuple[str, ...]

    def has(self, char: str) -> bool:
        return any(low <= ord(char) <= high for low, high in self.letters)


def _read(path: Path) -> Language:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Language(
        name=data["name"],
        letters=tuple((int(low, 16), int(high, 16)) for low, high in data["letters"]),
        prefixes=frozenset(plain(prefix) for prefix in data["prefixes"]),
        prefixes_together=int(data["prefixes_together"]),
        endings=tuple(sorted({plain(ending) for ending in data["endings"]}, key=len, reverse=True)),
        question_marks=tuple(data["question_marks"]),
        question_words=tuple(plain(words) for words in data["question_words"]),
    )


@cache
def languages() -> tuple[Language, ...]:
    """The languages of the files in this folder."""
    return tuple(_read(path) for path in sorted(FOLDER.glob("*.json")))


def language_of(word: str, known: tuple[Language, ...]) -> Language | None:
    """The language whose alphabet the first letter of a word is in; None for numbers, signs and emojis."""
    letter = next((char for char in word if char.isalpha()), None)
    if letter is None:
        return None
    return next((language for language in known if language.has(letter)), None)


def forms(word: str, known: tuple[Language, ...]) -> tuple[str, ...]:
    """A word as it is, and without the prefixes its language sticks to the start of words."""
    language = language_of(word, known)
    out = [word]
    if language is None:
        return tuple(out)
    for size in range(1, language.prefixes_together + 1):
        head, rest = word[:size], word[size:]
        if len(rest) >= 2 and all(char in language.prefixes for char in head):
            out.append(rest)
    return tuple(out)


def stem(word: str, known: tuple[Language, ...]) -> str:
    """A word without the longest ending its language allows, when what is left is long enough; numbers as they are."""
    if any(char.isdigit() for char in word):
        return word
    language = language_of(word, known)
    if language is None:
        return word
    for ending in language.endings:
        if word.endswith(ending) and len(word) - len(ending) >= SHORTEST_STEM:
            return word[: -len(ending)]
    return word


def asks(line: str, words: list[str], known: tuple[Language, ...]) -> bool:
    """Whether a line is a question: it has a question mark, or question words of a language, whole."""
    if any(mark in line for language in known for mark in language.question_marks):
        return True
    said = f" {' '.join(words)} "
    return any(f" {phrase} " in said for language in known for phrase in language.question_words)
