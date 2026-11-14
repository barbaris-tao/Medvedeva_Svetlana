"""Тесты параметров командной строки."""

import contextlib
import io
import os
import tempfile
import unittest

from depgraph.config import MODE_TEST, parse_args
from depgraph.errors import ConfigError

URL = "https://api.nuget.org/v3/index.json"


class ConfigTest(unittest.TestCase):
    """Проверка каждого пользовательского параметра."""

    def test_valid_remote(self):
        """Полная корректная конфигурация remote принимается."""
        config = parse_args(
            ["--package", "Newtonsoft.Json", "--repo", URL,
             "--version", "13.0.3", "--output", "out.svg"]
        )
        self.assertEqual(config.package, "Newtonsoft.Json")
        self.assertEqual(config.version, "13.0.3")

    def test_bad_package(self):
        """Имя пакета с недопустимыми символами отклоняется."""
        with self.assertRaises(ConfigError):
            parse_args(["--package", "bad name", "--repo", URL,
                        "--version", "1.0.0"])

    def test_bad_url(self):
        """Репозиторий, не являющийся HTTP(S)-URL, отклоняется."""
        with self.assertRaises(ConfigError):
            parse_args(["--package", "A", "--repo", "ftp://x",
                        "--version", "1.0.0"])

    def test_missing_version_remote(self):
        """В режиме remote версия обязательна."""
        with self.assertRaises(ConfigError):
            parse_args(["--package", "A", "--repo", URL])

    def test_bad_version(self):
        """Некорректно оформленная версия отклоняется."""
        with self.assertRaises(ConfigError):
            parse_args(["--package", "A", "--repo", URL,
                        "--version", "one.two"])

    def test_bad_output(self):
        """Выходной файл должен иметь расширение .svg."""
        with self.assertRaises(ConfigError):
            parse_args(["--package", "A", "--repo", URL,
                        "--version", "1.0", "--output", "out.png"])

    def test_missing_output_dir(self):
        """Каталог для выходного файла должен существовать."""
        with self.assertRaises(ConfigError):
            parse_args(["--package", "A", "--repo", URL, "--version",
                        "1.0", "--output", "/no/such/dir/out.svg"])

    def test_test_mode_missing_file(self):
        """Файл тестового репозитория должен существовать."""
        with self.assertRaises(ConfigError):
            parse_args(["--package", "A", "--repo", "/no/file.txt",
                        "--repo-mode", MODE_TEST])

    def test_test_mode_bad_package(self):
        """Тестовые пакеты именуются заглавными латинскими буквами."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "repo.txt")
            open(path, "w", encoding="utf-8").close()
            with self.assertRaises(ConfigError):
                parse_args(["--package", "a1", "--repo", path,
                            "--repo-mode", MODE_TEST])

    def test_unknown_mode(self):
        """Неизвестный режим репозитория отклоняется парсером."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(["--package", "A", "--repo", URL,
                            "--repo-mode", "other"])


if __name__ == "__main__":
    unittest.main()