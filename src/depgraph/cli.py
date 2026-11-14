"""Интерфейс командной строки инструмента."""

import sys
from typing import Optional, Sequence

from depgraph.config import MODE_TEST, Config, parse_args
from depgraph.d2 import render_svg, to_d2
from depgraph.errors import ConfigError, DepGraphError, RepositoryError
from depgraph.graph import (
    Repository,
    build_graph,
    format_graph,
    reverse_dependencies,
)
from depgraph.nuget import NuGetRepository
from depgraph.testrepo import load_test_repo

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_ERROR = 2


def print_config(config: Config) -> None:
    """Вывести все пользовательские параметры в виде пар «ключ — значение»."""
    for key, value in config.as_pairs():
        print(f"{key}: {value}")


def make_repository(config: Config) -> Repository:
    """Создать источник зависимостей, выбранный режимом репозитория."""
    if config.repo_mode == MODE_TEST:
        repo = load_test_repo(config.repo)
        if config.package not in repo:
            raise RepositoryError(
                f"пакет {config.package} не найден в тестовом репозитории"
            )
        return repo
    nuget = NuGetRepository(config.repo)
    nuget.set_version(config.package, config.version or "")
    return nuget


def run(config: Config) -> None:
    """Выполнить запрошенное действие."""
    repo = make_repository(config)
    if config.direct_only:
        deps = repo.dependencies(config.package)
        print("\n".join(deps) if deps else "Прямых зависимостей нет")
        return
    graph = build_graph(repo, config.package)
    if config.reverse:
        dependents = reverse_dependencies(graph, config.target or "")
        print("\n".join(dependents) if dependents else "Зависимых пакетов нет")
        return
    print(format_graph(graph))
    source = render_svg(to_d2(graph), config.output)
    print(f"D2: {source}\nSVG: {config.output}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Запустить инструмент и вернуть код завершения процесса."""
    try:
        config = parse_args(argv)
    except ConfigError as err:
        print(f"Ошибка конфигурации: {err}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    if config.show_config:
        print_config(config)
    try:
        run(config)
    except DepGraphError as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    return EXIT_OK