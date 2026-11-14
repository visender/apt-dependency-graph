"""Чтение прямых зависимостей из индекса пакетов Ubuntu."""

import gzip
import lzma
from urllib.request import urlopen

TIMEOUT = 30


def read_index(url):
    """Скачать текстовый индекс Packages, при необходимости распаковать."""
    with urlopen(url, timeout=TIMEOUT) as response:
        data = response.read()
    if data.startswith(b"\x1f\x8b"):
        data = gzip.decompress(data)
    elif data.startswith(b"\xfd7zXZ\x00"):
        data = lzma.decompress(data)
    return data.decode("utf-8")


def records(text):
    """Разобрать абзацы индекса и продолжения полей."""
    record = {}
    name = None
    for line in text.splitlines():
        if not line:
            if record:
                yield record
            record = {}
            name = None
        elif line[0].isspace() and name:
            record[name] += " " + line.strip()
        elif ":" in line:
            name, value = line.split(":", 1)
            record[name] = value.strip()
    if record:
        yield record


def direct_dependencies(text, package, version):
    """Найти точную версию и вернуть группы обязательных зависимостей."""
    for record in records(text):
        if record.get("Package") != package:
            continue
        if record.get("Version") == version:
            fields = (record.get("Pre-Depends", ""), record.get("Depends", ""))
            return [item.strip() for field in fields
                    for item in field.split(",") if item.strip()]
    raise ValueError(f"пакет {package} версии {version} не найден в индексе")
