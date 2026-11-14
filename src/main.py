"""Запуск прототипа анализатора зависимостей."""

import argparse
import lzma
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zlib import error as CompressionError

from apt_index import read_index
from graph import apt_graph, build_graph, read_test_graph, reverse_graph
from visualize import ascii_tree, save_graph

FIELDS = ("package", "repository", "test_mode", "version", "output", "ascii")
FLAGS = ("true", "false")
INVALID_PORT = 0
PACKAGE = r"[a-z0-9][a-z0-9+.-]+"
UPSTREAM = r"[0-9][a-zA-Z0-9.+~:-]*"
REVISION = r"[a-zA-Z0-9.+~]+"


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
    if not url.hostname.rstrip("."):
        raise ValueError("repository: некорректное имя хоста")
    if any(char.isspace() for char in value) or port == INVALID_PORT:
        raise ValueError("repository: некорректный URL")


def valid_version(value):
    """Проверить эпоху, основную версию и ревизию Debian."""
    epoch, colon, version = value.partition(":")
    if colon and not re.fullmatch(r"[0-9]+", epoch):
        return False
    upstream, dash, revision = (version if colon else value).rpartition("-")
    if dash and not re.fullmatch(REVISION, revision):
        return False
    return bool(re.fullmatch(UPSTREAM, upstream if dash else revision))


def validate_config(config, base):
    """Проверить значения всех настроек."""
    for name in FIELDS:
        if not config.get(name):
            raise ValueError(f"{name}: требуется значение")
    for name in ("test_mode", "ascii"):
        if config[name] not in FLAGS:
            raise ValueError(f"{name}: ожидается true или false")
    test_mode = config["test_mode"] == "true"
    pattern = r"[A-Z]" if test_mode else PACKAGE
    if not re.fullmatch(pattern, config["package"]):
        raise ValueError("package: недопустимое имя пакета")
    if not valid_version(config["version"]):
        raise ValueError("version: недопустимый формат версии")
    output = config["output"]
    if not re.fullmatch(r"[\w.-]+\.png", output, re.IGNORECASE):
        raise ValueError("output: требуется имя файла с расширением .png")
    validate_repository(config["repository"], test_mode, base)


def load_graph(config, base, reverse=False):
    """Получить граф из тестового файла или индекса Ubuntu."""
    package = config["package"]
    if config["test_mode"] == "true":
        index = read_test_graph(base / config["repository"])
        if package not in index:
            raise ValueError(f"пакет {package} не найден в тестовом графе")
        if reverse:
            return reverse_graph(package, index)
        return build_graph(package, index.__getitem__)
    return apt_graph(
        read_index(config["repository"]), package, config["version"], reverse
    )


def main():
    """Прочитать настройки и сохранить диаграмму зависимостей."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="путь к файлу XML")
    args = parser.parse_args()
    path = args.config
    try:
        config = read_config(path)
        validate_config(config, path.parent)
        graph = load_graph(config, path.parent)
        save_graph(graph, config["output"])
    except (OSError, ValueError, ElementTree.ParseError, EOFError,
            lzma.LZMAError, CompressionError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    if config["ascii"] == "true":
        for line in ascii_tree(config["package"], graph):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
