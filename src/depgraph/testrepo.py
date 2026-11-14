"""Тестовый репозиторий, описанный простым текстовым файлом.

Каждая строка имеет вид ``A: B C`` и означает, что пакет A зависит от
пакетов B и C. Имена пакетов — заглавные латинские буквы. Пустые строки
и текст после ``#`` игнорируются.
"""

import re
from typing import Dict, List

from depgraph.errors import RepositoryError
from depgraph.graph import DictRepository

NAME = r"[A-Z]+"
LINE_RE = re.compile(rf"^({NAME})\s*:(.*)$")
NAME_RE = re.compile(rf"^{NAME}$")


def _parse_line(number: int, line: str) -> tuple:
    """Разобрать одну непустую строку на пакет и его зависимости."""
    match = LINE_RE.match(line)
    if not match:
        raise RepositoryError(f"строка {number}: ожидается формат 'A: B C'")
    name, rest = match.groups()
    deps: List[str] = []
    for dep in rest.split():
        if not NAME_RE.match(dep):
            raise RepositoryError(f"строка {number}: плохое имя {dep!r}")
        if dep not in deps:
            deps.append(dep)
    return name, deps


def parse_test_repo(text: str) -> Dict[str, List[str]]:
    """Разобрать описание тестового репозитория."""
    graph: Dict[str, List[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name, deps = _parse_line(number, line)
        if name in graph:
            raise RepositoryError(f"строка {number}: повтор пакета {name}")
        graph[name] = deps
    for deps in list(graph.values()):
        for dep in deps:
            graph.setdefault(dep, [])
    return graph


def load_test_repo(path: str) -> DictRepository:
    """Прочитать тестовый репозиторий из файла."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as err:
        raise RepositoryError(f"{path}: {err}") from err
    return DictRepository(parse_test_repo(text))