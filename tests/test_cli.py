"""Проверки прототипа через командную строку."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "config.xml"


def run_cli(path):
    """Запустить программу и вернуть результат."""
    return subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py"), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


class CliTest(unittest.TestCase):
    """Проверки успешного запуска и ошибок XML."""

    def test_valid_config(self):
        """Вывести все шесть настроек."""
        result = run_cli(EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "package = hello",
            "repository = https://archive.ubuntu.com/ubuntu/",
            "test_mode = false",
            "version = 2.10-3",
            "output = graph.png",
            "ascii = false",
        ])

    def test_invalid_settings(self):
        """Отклонить неверное значение каждого поля."""
        invalid = {
            "package": ("hello", "?"),
            "repository": ("https://archive.ubuntu.com/ubuntu/", "local"),
            "test_mode": ("false", "maybe"),
            "version": ("2.10-3", "unknown"),
            "output": ("graph.png", "graph.txt"),
            "ascii": ("false", "maybe"),
        }
        source = EXAMPLE.read_text(encoding="utf-8")
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
