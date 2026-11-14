"""Построение графа зависимостей обходом в глубину."""

import re
from pathlib import Path

from apt_index import records
from deb_version import matches, version_key

DEPENDENCY = re.compile(
    r"\s*([a-z0-9][a-z0-9+.-]*)(?::[\w-]+)?"
    r"\s*(?:\((<<|<=|=|>=|>>)\s*([^\s)]+)\))?"
)


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


def requirements(record):
    """Извлечь имена и ограничения версий обязательных зависимостей."""
    fields = (record.get("Pre-Depends", ""), record.get("Depends", ""))
    for part in re.split(r"[,|]", ",".join(fields)):
        match = DEPENDENCY.match(part)
        if match:
            yield match.groups()


def compatible(index, requirement):
    """Вернуть версии из индекса, которые удовлетворяют ограничению."""
    name, relation, required = requirement
    return [(name, version) for version in index.get(name, ())
            if matches(version, relation, required)]


def forward_edges(index, node):
    """Выбрать старшую совместимую версию каждой зависимости."""
    name, version = node
    edges = []
    for requirement in requirements(index.get(name, {}).get(version, {})):
        child = requirement[0]
        candidates = compatible(index, requirement)
        if candidates:
            edges.append(max(candidates, key=lambda item: version_key(item[1])))
        elif child not in index:
            edges.append((child, ""))
    return edges


def reverse_edges(index):
    """Развернуть связи с учётом версий всех записей индекса."""
    parents = {}
    for name, versions in index.items():
        for version, record in versions.items():
            for requirement in requirements(record):
                for child in compatible(index, requirement):
                    parents.setdefault(child, []).append((name, version))
    return parents


def package_graph(graph):
    """Объединить посещённые версии в вершины по именам пакетов."""
    packages = {}
    for (name, _), children in graph.items():
        edges = packages.setdefault(name, {})
        for child, _ in children:
            edges[child] = None
    return {name: list(edges) for name, edges in packages.items()}


def reverse_graph(package, graph):
    """Обойти прямые и транзитивные обратные связи выбранного пакета."""
    parents = {node: [] for node in graph}
    for node, children in graph.items():
        for child in children:
            parents.setdefault(child, []).append(node)
    return build_graph(package, parents.__getitem__)


def apt_graph(text, package, version, reverse=False):
    """Обойти версии пакетов и представить результат по именам."""
    index = {}
    for record in records(text):
        name = record.get("Package")
        current = record.get("Version")
        if name and current:
            index.setdefault(name, {}).setdefault(current, record)
    if version not in index.get(package, {}):
        raise ValueError(f"пакет {package} версии {version} не найден")
    root = (package, version)
    if reverse:
        parents = reverse_edges(index)
        graph = build_graph(root, lambda node: parents.get(node, []))
        return package_graph(graph)
    graph = build_graph(root, lambda node: forward_edges(index, node))
    return package_graph(graph)
