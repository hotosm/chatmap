"""
Suggestions from the words of a map: a message is read line by line, and in
each line the places it names and the words of the values of its keys
("مسكر" for Closed) make a suggestion each: this place, this value. A person
confirms each one; nothing here changes a place.

A bulletin, one message with a line per place, gives a suggestion per line.
A word matches a whole word of the message, as it is typed or with a prefix
its language sticks to it ("وتفتيش" is "و" and "تفتيش"); a word of a value
also matches the same word with another ending its language allows
("سالكات" says "سالك", "cerrada" says "cerrado"); a number only matches
itself ("حاجز 17" is not "حاجز 170"). What each language allows is data,
in recognition/languages, and a word is read with the rules of its alphabet.

What a line says goes to the place nearest to it in the line, and a line
that names no place speaks of the place of its group, when the group has
only one. A suggestion is doubtful when its line asks, or says two values of
the same key of a place: it is still made, and says why it is doubtful.
"""
import re
from dataclasses import dataclass, field

from recognition.languages import Language, asks, forms, languages, stem
from recognition.text import plain

QUESTION = "question"
TWO_VALUES = "two_values"

# A word with the marks written on its letters (Arabic vowels, Hebrew niqqud, the tatweel), or a sign or emoji alone
_MARKS = "\u0300-\u036f\u0591-\u05c7\u0610-\u061a\u0640\u064b-\u065f\u0670\u06d6-\u06ed"
_TOKEN = re.compile(rf"(?:\w|[{_MARKS}])+|[^\w\s\ufe0f{_MARKS}]", re.UNICODE)


@dataclass(frozen=True)
class Place:
    id: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class Value:
    id: str
    key_id: str
    words: tuple[str, ...]


@dataclass(frozen=True)
class Suggestion:
    """
    This place, this value, said in this line (counted from 0) by these words
    as the message writes them; and why it is doubtful, if it is.
    """
    line: int
    point_id: str
    key_id: str
    value_id: str
    words: tuple[str, ...]
    doubt: str | None = None


def _spans(text: str) -> list[tuple[str, int, int]]:
    """The words of a text made plain, each with where it is written; a sign or emoji is a word by itself."""
    found = ((plain(match.group()), match.start(), match.end()) for match in _TOKEN.finditer(text))
    return [(word, start, end) for word, start, end in found if word]


def tokens(text: str) -> list[str]:
    """The words of a text made plain, and each sign or emoji by itself (without the mark that makes it colored)."""
    return [word for word, _, _ in _spans(text)]


@dataclass(frozen=True)
class _Entry:
    words: tuple[str, ...]
    kind: str            # "place" or "value"
    item: Place | Value


@dataclass
class _Found:
    start: int
    end: int
    entry: _Entry


@dataclass
class Reader:
    """
    The words of a map, ready to read its messages: by their first word, the
    longest first; the words of values of one word also by their stem; and
    the languages they are read with.
    """
    known: tuple[Language, ...]
    by_first: dict[str, list[_Entry]] = field(default_factory=dict)
    stems: dict[str, list[_Entry]] = field(default_factory=dict)


def compile_map(places: list[Place], values: list[Value], known: tuple[Language, ...] | None = None) -> Reader:
    reader = Reader(known=languages() if known is None else known)
    entries = [
        _Entry(tuple(tokens(name)), "place", place) for place in places for name in place.names
    ] + [
        _Entry(tuple(tokens(word)), "value", value) for value in values for word in value.words
    ]
    for entry in entries:
        if not entry.words:
            continue
        reader.by_first.setdefault(entry.words[0], []).append(entry)
        # A value said in one word also takes it with another ending
        if entry.kind == "value" and len(entry.words) == 1:
            reader.stems.setdefault(stem(entry.words[0], reader.known), []).append(entry)
    for found in reader.by_first.values():
        # The longest first, and a place before a value of the same length
        found.sort(key=lambda entry: (-len(entry.words), entry.kind != "place"))
    return reader


def _match_at(reader: Reader, line: list[str], start: int) -> _Found | None:
    """The longest name or word that starts at a word of a line."""
    written = forms(line[start], reader.known)
    for form in written:
        for entry in reader.by_first.get(form, []):
            rest = entry.words[1:]
            if tuple(line[start + 1:start + 1 + len(rest)]) == rest:
                return _Found(start, start + len(entry.words), entry)
    for form in written:
        found = reader.stems.get(stem(form, reader.known))
        if found:
            return _Found(start, start + 1, found[0])
    return None


def _found_in(reader: Reader, line: list[str]) -> list[_Found]:
    found, at = [], 0
    while at < len(line):
        hit = _match_at(reader, line, at)
        if hit:
            found.append(hit)
            at = hit.end
        else:
            at += 1
    return found


def _nearest(place_hits: list[_Found], value_hit: _Found) -> _Found:
    """The place nearest to what a value says; on a tie, the one before it."""
    def distance(place: _Found) -> tuple[int, int]:
        if place.end <= value_hit.start:
            return value_hit.start - place.end, 0
        return place.start - value_hit.end, 1
    return min(place_hits, key=distance)


def _written(raw: str, spans: list[tuple[str, int, int]], hit: _Found) -> str:
    """What matched, as the message writes it."""
    return raw[spans[hit.start][1]:spans[hit.end - 1][2]]


def read(reader: Reader, text: str, group_places: tuple[str, ...] = ()) -> list[Suggestion]:
    """What a message suggests, line by line, in the order its lines say it."""
    suggestions: list[Suggestion] = []
    for number, raw in enumerate((text or "").split("\n")):
        spans = _spans(raw)
        line = [word for word, _, _ in spans]
        if not line:
            continue
        found = _found_in(reader, line)
        place_hits = [hit for hit in found if hit.entry.kind == "place"]
        value_hits = [hit for hit in found if hit.entry.kind == "value"]
        if not value_hits:
            continue
        question = asks(raw, line, reader.known)
        said: dict[tuple[str, str], list[tuple[Value, tuple[str, ...]]]] = {}
        for hit in value_hits:
            value: Value = hit.entry.item
            if place_hits:
                place_hit = _nearest(place_hits, hit)
                point_id = place_hit.entry.item.id
                words = (_written(raw, spans, place_hit), _written(raw, spans, hit))
            elif len(group_places) == 1:
                point_id, words = group_places[0], (_written(raw, spans, hit),)
            else:
                continue
            said.setdefault((point_id, value.key_id), []).append((value, words))
        for (point_id, key_id), values in said.items():
            distinct = {value.id for value, _ in values}
            doubt = QUESTION if question else TWO_VALUES if len(distinct) > 1 else None
            # One suggestion for each value, with every word of the line that says it ("🔴 ... cerrado")
            merged: dict[str, tuple[Value, list[str]]] = {}
            for value, words in values:
                kept = merged.setdefault(value.id, (value, []))[1]
                kept.extend(word for word in words if word not in kept)
            for value, words in merged.values():
                suggestions.append(Suggestion(number, point_id, key_id, value.id, tuple(words), doubt))
    return suggestions
