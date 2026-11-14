"""Экспорт графа и вывод дерева зависимостей."""

import subprocess
from pathlib import Path


def mermaid(graph):
    """Описать вершины и рёбра в формате Mermaid."""
    ids = {name: f"n{number}" for number, name in enumerate(graph)}
    lines = ["flowchart TD"]
    for name, key in ids.items():
        lines.append(f'    {key}["{name}"]')
    for name, children in graph.items():
        lines.extend(f"    {ids[name]} --> {ids[node]}" for node in children)
    return "\n".join(lines) + "\n"


def save_graph(graph, output):
    """Сохранить PNG через Graphviz и текст диаграммы рядом с ним."""
    path = Path(output)
    lines = ["digraph dependencies {"]
    for name, children in graph.items():
        lines.append(f'    "{name}";')
        lines.extend(f'    "{name}" -> "{node}";' for node in children)
    lines.append("}")
    try:
        result = subprocess.run(
            ["dot", "-Tpng"], input="\n".join(lines).encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
    except FileNotFoundError as error:
        raise ValueError("установите Graphviz и добавьте dot в PATH") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Graphviz: {message}") from error
    path.write_bytes(result.stdout)
    path.with_suffix(".mmd").write_text(mermaid(graph), encoding="utf-8")


def ascii_tree(package, graph):
    """Вывести дерево со ссылками на уже показанные вершины."""
    stack = [(package, "")]
    shown = set()
    while stack:
        node, prefix = stack.pop()
        if node in shown:
            yield f"{prefix}{node} [*]"
            continue
        yield f"{prefix}{node}"
        shown.add(node)
        indent = " " * len(prefix) + "+-- "
        stack.extend((child, indent) for child in reversed(graph[node]))
