"""Построение графа зависимостей обходом в глубину."""

import re
from pathlib import Path

from apt_index import records


def build_graph(package, dependencies):
    """Обойти граф со стеком и обработать каждый пакет один раз."""
    graph = {}
    stack = [package]
    while stack:
        node = stack.pop()
        if node in graph:
            continue
        graph[node] = dependencies(node)
        stack.extend(reversed(graph[node]))
    return graph


def read_test_graph(path):
    """Прочитать строки вида A: B C и добавить неописанные листья."""
    graph = {}
    for number, line in enumerate(Path(path).read_text(
            encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        name, separator, children = line.partition(":")
        name = name.strip()
        nodes = children.split()
        if not separator or name in graph or not all(
                re.fullmatch(r"[A-Z]", node) for node in [name, *nodes]):
            raise ValueError(f"{path}:{number}: неверная строка графа")
        graph[name] = list(dict.fromkeys(nodes))
    for children in list(graph.values()):
        for node in children:
            graph.setdefault(node, [])
    return graph


def dependency_names(record):
    """Извлечь имена вариантов из обязательных зависимостей."""
    fields = (record.get("Pre-Depends", ""), record.get("Depends", ""))
    names = {}
    for part in re.split(r"[,|]", ",".join(fields)):
        match = re.match(r"\s*([a-z0-9][a-z0-9+.-]*)", part)
        if match:
            names[match.group(1)] = None
    return list(names)


def apt_graph(text, package, version):
    """Построить граф с точной версией корня и первым совпадением потомков."""
    index = {}
    selected = None
    for record in records(text):
        name = record.get("Package")
        if name:
            index.setdefault(name, record)
        if name == package and record.get("Version") == version:
            selected = record
    if selected is None:
        raise ValueError(f"пакет {package} версии {version} не найден")
    index[package] = selected
    return build_graph(package, lambda node: dependency_names(
        index.get(node, {})
    ))
