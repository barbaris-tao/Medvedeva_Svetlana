"""Тесты построения графа и тестового репозитория."""

import io
import os
import contextlib
import unittest
from unittest import mock

from depgraph.cli import main
from depgraph.errors import RepositoryError
from depgraph.graph import (
    DictRepository,
    build_graph,
    format_graph,
    invert,
    reverse_dependencies,
)
from depgraph.testrepo import load_test_repo, parse_test_repo

DATA = os.path.join(os.path.dirname(__file__), "data")


def data_path(name):
    """Вернуть путь к файлу тестового репозитория."""
    return os.path.join(DATA, name)


def graph_of(name, root):
    """Построить граф по файлу тестового репозитория."""
    return build_graph(load_test_repo(data_path(name)), root)


class BuildGraphTest(unittest.TestCase):
    """Поведение построения графа обходом в ширину (BFS)."""

    def test_tree(self):
        """Транзитивные зависимости собираются в порядке BFS."""
        graph = graph_of("tree.txt", "A")
        self.assertEqual(list(graph), ["A", "B", "C", "D", "E"])
        self.assertEqual(graph["C"], ["D", "E"])

    def test_subgraph(self):
        """Включаются только пакеты, достижимые из корня."""
        self.assertEqual(list(graph_of("tree.txt", "C")), ["C", "D", "E"])

    def test_cycle(self):
        """Циклические зависимости не приводят к бесконечному обходу."""
        graph = graph_of("cycle.txt", "A")
        self.assertEqual(graph, {"A": ["B"], "B": ["C", "D"],
                                 "C": ["A"], "D": ["D"]})

    def test_diamond_and_undeclared(self):
        """Общие и необъявленные пакеты появляются ровно один раз."""
        graph = graph_of("diamond.txt", "A")
        self.assertEqual(list(graph), ["A", "B", "C", "D", "F", "E"])
        self.assertEqual(graph["F"], [])

    def test_single_package(self):
        """Пакет без зависимостей даёт граф из одного узла."""
        self.assertEqual(build_graph(DictRepository({"A": []}), "A"),
                         {"A": []})

    def test_format(self):
        """Текстовая форма перечисляет зависимости каждого пакета."""
        text = format_graph(graph_of("tree.txt", "B"))
        self.assertEqual(text, "B -> D\nD")


class ReverseTest(unittest.TestCase):
    """Поведение поиска обратных зависимостей."""

    def test_invert(self):
        """Рёбра обращаются."""
        self.assertEqual(invert({"A": ["B"], "B": []}),
                         {"A": [], "B": ["A"]})

    def test_transitive_dependents(self):
        """Прямые и транзитивные зависимые пакеты находятся в порядке BFS."""
        graph = graph_of("diamond.txt", "A")
        self.assertEqual(reverse_dependencies(graph, "D"), ["B", "C", "A"])

    def test_leaf_dependents(self):
        """Общий лист требуется всем, кто находится выше него."""
        graph = graph_of("tree.txt", "A")
        self.assertEqual(reverse_dependencies(graph, "E"), ["C", "A"])

    def test_root_has_no_dependents(self):
        """У корня ациклического графа нет зависимых пакетов."""
        graph = graph_of("tree.txt", "A")
        self.assertEqual(reverse_dependencies(graph, "A"), [])

    def test_cycle(self):
        """Циклы обрабатываются, и члены зависят друг от друга."""
        graph = graph_of("cycle.txt", "A")
        self.assertEqual(reverse_dependencies(graph, "A"), ["C", "B"])

    def test_unknown_target(self):
        """Цель вне графа является ошибкой."""
        with self.assertRaises(RepositoryError):
            reverse_dependencies(graph_of("tree.txt", "A"), "Z")


class ParseTest(unittest.TestCase):
    """Разбор файлов тестового репозитория."""

    def test_bad_line(self):
        """Строка без двоеточия отклоняется."""
        with self.assertRaises(RepositoryError):
            parse_test_repo("A B")

    def test_bad_name(self):
        """Имя пакета в нижнем регистре отклоняется."""
        with self.assertRaises(RepositoryError):
            parse_test_repo("A: b")

    def test_duplicate(self):
        """Пакет, описанный дважды, отклоняется."""
        with self.assertRaises(RepositoryError):
            parse_test_repo("A: B\nA: C")

    def test_duplicate_dependency(self):
        """Повторяющиеся зависимости схлопываются."""
        self.assertEqual(parse_test_repo("A: B B")["A"], ["B"])


class CliTest(unittest.TestCase):
    """Поведение командной строки в тестовом режиме."""

    def run_cli(self, *args):
        """Запустить CLI и вернуть (код завершения, stdout)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()), \
                mock.patch("depgraph.cli.render_svg",
                           return_value="graph.d2") as render:
            code = main(list(args))
        self.render = render
        return code, out.getvalue()

    def test_graph_output(self):
        """CLI выводит граф тестового репозитория."""
        code, out = self.run_cli(
            "--package", "A", "--repo", data_path("cycle.txt"),
            "--repo-mode", "test")
        self.assertEqual(code, 0)
        self.assertIn("C -> A", out)
        self.render.assert_called_once()

    def test_reverse_output(self):
        """CLI выводит обратные зависимости целевого пакета."""
        code, out = self.run_cli(
            "--package", "A", "--repo", data_path("tree.txt"),
            "--repo-mode", "test", "--reverse", "--target", "D")
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), ["B", "C", "A"])
        self.render.assert_not_called()

    def test_reverse_requires_target(self):
        """--reverse без --target — ошибка конфигурации."""
        code, _ = self.run_cli(
            "--package", "A", "--repo", data_path("tree.txt"),
            "--repo-mode", "test", "--reverse")
        self.assertEqual(code, 2)

    def test_unknown_root(self):
        """Неизвестный корневой пакет даёт ошибку времени выполнения."""
        code, _ = self.run_cli(
            "--package", "Z", "--repo", data_path("tree.txt"),
            "--repo-mode", "test")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()