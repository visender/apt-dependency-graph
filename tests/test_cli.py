"""Проверки прототипа через командную строку."""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "config.xml"


INDEX = (
    "Package: hello\nVersion: 1.0\nDepends: old\n\n"
    "Package: hello\nVersion: 2.10-3build1\nPre-Depends: shell\n"
    "Depends: libc6 (>= 2.38),\n editor | vim\nRecommends: extra\n"
)


def run_cli(path, directory=None):
    """Запустить программу и вернуть результат."""
    return subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py"), str(path)],
        cwd=directory,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )


class CliTest(unittest.TestCase):
    """Проверки успешного запуска и ошибок XML."""

    @unittest.skipUnless(shutil.which("dot"), "Нужен Graphviz")
    def test_direct_dependencies(self):
        """Построить граф из записи с нужной версией корня."""
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "Packages").write_text(INDEX, encoding="utf-8")
            handler = partial(SimpleHTTPRequestHandler, directory=directory)
            result = self.run_server(handler)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "hello", "+-- shell", "+-- libc6", "+-- editor", "+-- vim",
        ])

    def run_server(self, handler):
        """Запустить временный HTTP-сервер для проверки CLI."""
        with HTTPServer(("127.0.0.1", 0), handler) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                return self.run_with_index(server.server_port)
            finally:
                server.shutdown()
                worker.join()

    @unittest.skipUnless(shutil.which("dot"), "Нужен Graphviz")
    def test_cycle(self):
        """Сохранить диаграмму цикла и закончить вывод дерева."""
        source = EXAMPLE.with_name("cycle.xml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.xml"
            graph = EXAMPLE.with_name("cycle.txt").as_posix()
            xml = source.replace("cycle.txt", graph)
            path.write_text(xml.replace(">false<", ">true<"), encoding="utf-8")
            result = run_cli(path, directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("A [*]", result.stdout)
            png = (path.parent / "graph.png").read_bytes()
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
            diagram = (path.parent / "graph.mmd").read_text()
            self.assertIn("n2 --> n0", diagram)

    def run_with_index(self, port):
        """Подставить адрес локального HTTP-сервера в XML."""
        source = EXAMPLE.read_text(encoding="utf-8")
        xml = source.replace(
            source.split("<repository>")[1].split("</repository>")[0],
            f"http://127.0.0.1:{port}/Packages",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.xml"
            xml = xml.replace("<ascii>false", "<ascii>true")
            path.write_text(xml, encoding="utf-8")
            return run_cli(path, directory)

    def test_invalid_settings(self):
        """Отклонить неверное значение каждого поля."""
        invalid = {
            "package": ("hello", "?"),
            "repository": (None, "local"),
            "test_mode": ("false", "maybe"),
            "version": ("2.10-3build1", "unknown"),
            "output": ("graph.png", "graph.txt"),
            "ascii": ("false", "maybe"),
        }
        source = EXAMPLE.read_text(encoding="utf-8")
        repository = source.split("<repository>")[1].split("</repository>")[0]
        invalid["repository"] = (repository, "local")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.xml"
            for name, (valid, wrong) in invalid.items():
                with self.subTest(name=name):
                    xml = source.replace(
                        f"<{name}>{valid}</{name}>", f"<{name}>{wrong}</{name}>"
                    )
                    path.write_text(xml, encoding="utf-8")
                    result = run_cli(path)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(f"{name}:", result.stderr)
