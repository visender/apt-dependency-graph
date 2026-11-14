"""Проверки выбора версии при построении графа."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from graph import apt_graph

INDEX = (
    "Package: hello\nVersion: 2\nDepends: libfoo (>= 2)\n\n"
    "Package: libfoo\nVersion: 1\nDepends: olddep\n\n"
    "Package: libfoo\nVersion: 2\nDepends: newdep\n\n"
    "Package: users\nVersion: 3\nDepends: hello (<< 2)\n\n"
    "Package: users\nVersion: 2\nDepends: hello (= 2)\n"
)


class VersionGraphTest(unittest.TestCase):
    """Проверить ограничения в прямом и обратном обходе."""

    def test_forward(self):
        """Раскрыть зависимости подходящей версии."""
        graph = apt_graph(INDEX, "hello", "2")
        self.assertEqual(graph["libfoo"], ["newdep"])

    def test_reverse(self):
        """Найти совместимый пакет среди нескольких записей."""
        graph = apt_graph(INDEX, "hello", "2", reverse=True)
        self.assertEqual(graph["hello"], ["users"])
        older_only = INDEX.rsplit("\n\n", 1)[0]
        graph = apt_graph(older_only, "hello", "2", reverse=True)
        self.assertEqual(graph["hello"], [])
