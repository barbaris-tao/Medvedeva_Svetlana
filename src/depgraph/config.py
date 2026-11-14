"""Конфигурация инструмента, полученная из параметров командной строки."""

import argparse
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from depgraph.errors import ConfigError

MODE_REMOTE = "remote"
MODE_TEST = "test"
REPO_MODES = (MODE_REMOTE, MODE_TEST)
URL_SCHEMES = ("http", "https")
SVG_SUFFIX = ".svg"
DEFAULT_OUTPUT = "graph.svg"

NUGET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
TEST_ID_RE = re.compile(r"^[A-Z]+$")
VERSION_RE = re.compile(
    r"^\d+(\.\d+){0,3}(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$"
)


@dataclass(frozen=True)
class Config:
    """Проверенные параметры, заданные пользователем."""

    package: str
    repo: str
    repo_mode: str
    version: Optional[str]
    output: str
    show_config: bool = False
    direct_only: bool = False
    reverse: bool = False
    target: Optional[str] = None

    def as_pairs(self) -> List[Tuple[str, str]]:
        """Вернуть параметры в виде пар (ключ, значение)."""
        return [
            ("package", self.package),
            ("repo", self.repo),
            ("repo_mode", self.repo_mode),
            ("version", self.version or "-"),
            ("output", self.output),
        ]


def _add_input_options(parser: argparse.ArgumentParser) -> None:
    """Добавить опции, описывающие анализируемый пакет и репозиторий."""
    parser.add_argument(
        "--package", required=True, help="имя анализируемого пакета"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="URL репозитория (service index) или путь к файлу "
        "тестового репозитория",
    )
    parser.add_argument(
        "--repo-mode",
        choices=REPO_MODES,
        default=MODE_REMOTE,
        help="режим работы с репозиторием: remote или test",
    )
    parser.add_argument("--version", help="версия пакета")


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    """Добавить опции, выбирающие результат и имя его файла."""
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="имя файла с изображением графа (.svg)",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="вывести параметры в формате ключ-значение",
    )
    parser.add_argument(
        "--direct-only",
        action="store_true",
        help="вывести только прямые зависимости пакета",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="вывести обратные зависимости пакета --target",
    )
    parser.add_argument(
        "--target",
        help="пакет графа, чьи обратные зависимости нужны (с --reverse)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер командной строки."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Визуализация графа зависимостей пакетов NuGet.",
    )
    _add_input_options(parser)
    _add_output_options(parser)
    return parser


def validate_package(package: str, repo_mode: str) -> str:
    """Проверить имя пакета на соответствие правилам режима репозитория."""
    pattern = TEST_ID_RE if repo_mode == MODE_TEST else NUGET_ID_RE
    if not pattern.match(package):
        raise ConfigError(f"некорректное имя пакета: {package!r}")
    return package


def validate_repo(repo: str, repo_mode: str) -> str:
    """Проверить, что репозиторий является URL или существующим файлом."""
    if repo_mode == MODE_TEST:
        if not os.path.isfile(repo):
            raise ConfigError(f"файл тестового репозитория не найден: {repo}")
        return repo
    parsed = urlparse(repo)
    if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
        raise ConfigError(f"некорректный URL репозитория: {repo!r}")
    return repo


def validate_version(version: Optional[str], repo_mode: str) -> Optional[str]:
    """Проверить версию пакета; она обязательна в режиме remote."""
    if version is None:
        if repo_mode == MODE_REMOTE:
            raise ConfigError("в режиме remote необходимо указать --version")
        return None
    if not VERSION_RE.match(version):
        raise ConfigError(f"некорректная версия пакета: {version!r}")
    return version


def validate_output(output: str) -> str:
    """Проверить, что имя выходного файла — это SVG-файл в существующем каталоге."""
    name = os.path.basename(output).lower()
    if not name.endswith(SVG_SUFFIX) or name == SVG_SUFFIX:
        raise ConfigError(f"файл изображения должен быть .svg: {output!r}")
    folder = os.path.dirname(output) or "."
    if not os.path.isdir(folder):
        raise ConfigError(f"каталог для изображения не найден: {folder}")
    return output


def validate_target(
    target: Optional[str], reverse: bool, repo_mode: str
) -> Optional[str]:
    """Проверить --target: он обязателен с --reverse и только тогда."""
    if reverse and target is None:
        raise ConfigError("для --reverse необходимо указать --target")
    if target is not None and not reverse:
        raise ConfigError("--target используется только вместе с --reverse")
    if target is not None:
        validate_package(target, repo_mode)
    return target


def parse_args(argv: Optional[Sequence[str]] = None) -> Config:
    """Разобрать и проверить параметры командной строки."""
    args = build_parser().parse_args(argv)
    mode = args.repo_mode
    return Config(
        package=validate_package(args.package, mode),
        repo=validate_repo(args.repo, mode),
        repo_mode=mode,
        version=validate_version(args.version, mode),
        output=validate_output(args.output),
        show_config=args.show_config,
        direct_only=args.direct_only,
        reverse=args.reverse,
        target=validate_target(args.target, args.reverse, mode),
    )