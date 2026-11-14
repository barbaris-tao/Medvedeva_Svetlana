"""Построение графа зависимостей и текстовый вывод."""

from typing import Dict, Iterable, List, Protocol

from depgraph.errors import RepositoryError

Graph = Dict[str, List[str]]


class Repository(Protocol):
    """Всё, что умеет перечислять прямые зависимости пакета."""

    def dependencies(self, name: str) -> List[str]:
        """Вернуть имена прямых зависимостей пакета."""


class DictRepository:
    """Репозиторий, основанный на словаре смежности."""

    def __init__(self, adjacency: Dict[str, Iterable[str]]):
        """Сохранить данные смежности."""
        self._adjacency = {k: list(v) for k, v in adjacency.items()}

    def __contains__(self, name: str) -> bool:
        """Сообщить, известен ли пакет репозиторию."""
        return name in self._adjacency

    def dependencies(self, name: str) -> List[str]:
        """Вернуть прямые зависимости; у неизвестных пакетов их нет."""
        return list(self._adjacency.get(name, []))


def _visit_level(repo: Repository, level: List[str], graph: Graph) -> None:
    """Обработать один уровень BFS и рекурсивно перейти к следующему."""
    next_level: List[str] = []
    for name in level:
        if name in graph:
            continue
        deps = repo.dependencies(name)
        graph[name] = deps
        next_level.extend(dep for dep in deps if dep not in graph)
    if next_level:
        _visit_level(repo, next_level, graph)


def build_graph(repo: Repository, root: str) -> Graph:
    """Построить транзитивный граф зависимостей рекурсивным BFS.

    Пакеты раскрываются один раз, поэтому циклические зависимости завершаются.
    """
    graph: Graph = {}
    _visit_level(repo, [root], graph)
    return graph


def format_graph(graph: Graph) -> str:
    """Представить граф в виде текста, по одному пакету на строку."""
    lines = []
    for name, deps in graph.items():
        lines.append(f"{name} -> {', '.join(deps)}" if deps else f"{name}")
    return "\n".join(lines)


def invert(graph: Graph) -> Graph:
    """Вернуть граф со всеми обращёнными рёбрами."""
    inverted: Graph = {name: [] for name in graph}
    for name, deps in graph.items():
        for dep in deps:
            inverted.setdefault(dep, []).append(name)
    return inverted


def reverse_dependencies(graph: Graph, target: str) -> List[str]:
    """Вернуть пакеты графа, которые зависят от target.

    Зависимые пакеты находятся тем же BFS, что и граф зависимостей,
    но запущенным по обращённым рёбрам начиная с пакета target.
    """
    if target not in graph:
        raise RepositoryError(f"пакет {target} отсутствует в графе")
    reached = build_graph(DictRepository(invert(graph)), target)
    return [name for name in reached if name != target]