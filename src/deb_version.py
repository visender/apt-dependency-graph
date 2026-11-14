"""Сравнение версий пакетов Debian."""

import re

PARTS = re.compile(r"([0-9]+)")
END = ((0,), 0)
LAST_PAIR = -1
RELATIONS = {
    "<<": {-1}, "<=": {-1, 0}, "=": {0}, ">=": {0, 1}, ">>": {1},
}


def order(char):
    """Вернуть порядок символа в нечисловой части."""
    if char == "~":
        return -1
    if not char:
        return 0
    return ord(char) if char.isalpha() else ord(char) + 256


def part_key(value):
    """Разделить часть версии на сравнимые текстовые и числовые пары."""
    pieces = PARTS.split(value)
    pairs = []
    for letters, digits in zip(pieces[::2], [*pieces[1::2], "0"]):
        pairs.append((tuple(map(order, letters)) + (0,), int(digits or "0")))
    while pairs and pairs[LAST_PAIR] == END:
        pairs.pop()
    return [*pairs, END]


def version_key(value):
    """Учесть эпоху, основную версию и ревизию."""
    epoch, colon, body = value.partition(":")
    upstream, dash, revision = (body if colon else value).rpartition("-")
    return (
        int(epoch) if colon else 0,
        part_key(upstream if dash else revision),
        part_key(revision if dash else "0"),
    )


def matches(version, relation, required):
    """Проверить ограничение из Depends или Pre-Depends."""
    if not relation:
        return True
    left, right = version_key(version), version_key(required)
    return ((left > right) - (left < right)) in RELATIONS[relation]
