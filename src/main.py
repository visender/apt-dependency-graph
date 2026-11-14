"""Запуск прототипа анализатора зависимостей."""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

FIELDS = ("package", "repository", "test_mode", "version", "output", "ascii")
FLAGS = ("true", "false")
INVALID_PORT = 0
PACKAGE = r"[a-z0-9][a-z0-9+.-]+"
VERSION = r"(?:[0-9]+:)?[0-9][a-zA-Z0-9.+~:-]*"


def read_config(path):
    """Прочитать XML и проверить состав полей."""
    root = ElementTree.parse(path).getroot()
    if root.tag != "config" or root.attrib:
        raise ValueError("корневой элемент должен быть <config> без атрибутов")
    config = {}
    for node in root:
        if node.tag not in FIELDS or node.tag in config:
            raise ValueError(f"лишнее или повторное поле: {node.tag}")
        if node.attrib or len(node):
            raise ValueError(f"{node.tag}: ожидается текстовое значение")
        config[node.tag] = (node.text or "").strip()
    for name in FIELDS:
        if not config.get(name):
            raise ValueError(f"{name}: требуется значение")
    return config


def validate_repository(value, test_mode, base):
    """Проверить путь к тестовому файлу или адрес репозитория."""
    if test_mode:
        if not (base / value).is_file():
            raise ValueError("repository: тестовый файл не найден")
        return
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError as error:
        raise ValueError("repository: некорректный URL") from error
    if url.scheme not in ("http", "https") or not url.hostname:
        raise ValueError("repository: нужен URL с http или https")
    if any(char.isspace() for char in value) or port == INVALID_PORT:
        raise ValueError("repository: некорректный URL")


def validate_config(config, base):
    """Проверить значения всех настроек."""
    for name in ("test_mode", "ascii"):
        if config[name] not in FLAGS:
            raise ValueError(f"{name}: ожидается true или false")
    test_mode = config["test_mode"] == "true"
    pattern = r"[A-Z]" if test_mode else PACKAGE
    if not re.fullmatch(pattern, config["package"]):
        raise ValueError("package: недопустимое имя пакета")
    if not re.fullmatch(VERSION, config["version"]):
        raise ValueError("version: недопустимый формат версии")
    output = config["output"]
    if not re.fullmatch(r"[\w.-]+\.png", output, re.IGNORECASE):
        raise ValueError("output: требуется имя файла с расширением .png")
    validate_repository(config["repository"], test_mode, base)


def main():
    """Прочитать XML и напечатать настройки."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="путь к файлу XML")
    path = parser.parse_args().config
    try:
        config = read_config(path)
        validate_config(config, path.parent)
    except (OSError, ValueError, ElementTree.ParseError) as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return 1
    for name in FIELDS:
        print(f"{name} = {config[name]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
