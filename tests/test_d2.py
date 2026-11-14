"""Тесты генерации D2 и рендеринга."""

import os
import tempfile
import unittest
from unittest import mock

from depgraph import d2
from depgraph.errors import RenderError


class D2Test(unittest.TestCase):
    """Генерация текста D2 и обёртка рендеринга."""

    def test_edges_and_isolated_nodes(self):
        """Записываются рёбра и узлы без зависимостей."""
        text = d2.to_d2({"A": ["B"], "B": []})
        self.assertEqual(text, '"A" -> "B"\n"B"\n')

    def test_dots_are_quoted(self):
        """Идентификаторы NuGet с точками остаются одиночными узлами."""
        text = d2.to_d2({"Newtonsoft.Json": ["System.Memory"]})
        self.assertEqual(text, '"Newtonsoft.Json" -> "System.Memory"\n')

    def test_quote_escapes(self):
        """Кавычки и обратные слэши экранируются."""
        self.assertEqual(d2.quote('a"b\\c'), '"a\\"b\\\\c"')

    def test_missing_d2_program(self):
        """Отсутствие программы d2 даёт понятную ошибку, исходник сохраняется."""
        with tempfile.TemporaryDirectory() as folder:
            output = os.path.join(folder, "g.svg")
            with mock.patch.object(d2, "D2_BINARY", "no-such-d2-binary"):
                with self.assertRaises(RenderError):
                    d2.render_svg('"A"\n', output)
            self.assertTrue(os.path.isfile(os.path.join(folder, "g.d2")))

    def test_render_calls_d2(self):
        """Программа d2 вызывается с путями исходника и результата."""
        with tempfile.TemporaryDirectory() as folder:
            output = os.path.join(folder, "g.svg")
            with mock.patch("subprocess.run") as run:
                source = d2.render_svg('"A"\n', output)
            run.assert_called_once()
            self.assertEqual(run.call_args[0][0][1:], [source, output])


if __name__ == "__main__":
    unittest.main()