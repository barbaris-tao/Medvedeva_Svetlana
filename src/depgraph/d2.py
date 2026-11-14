"""Преобразование графа в D2 и рендеринг SVG-изображений."""

import os
import subprocess

from depgraph.errors import RenderError
from depgraph.graph import Graph

D2_BINARY = "d2"
D2_SUFFIX = ".d2"


def quote(name: str) -> str:
    """Заключить имя пакета в кавычки, чтобы точки не воспринимались как вложенность."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def to_d2(graph: Graph) -> str:
    """Вернуть текст диаграммы D2 для графа зависимостей."""
    lines = []
    for name, deps in graph.items():
        if not deps:
            lines.append(quote(name))
        lines.extend(f"{quote(name)} -> {quote(dep)}" for dep in deps)
    return "\n".join(lines) + "\n"


def source_path(output: str) -> str:
    """Вернуть путь к файлу .d2, сохраняемому рядом с изображением."""
    return os.path.splitext(output)[0] + D2_SUFFIX


def render_svg(d2_text: str, output: str) -> str:
    """Сохранить текст D2 и отрендерить его в SVG программой d2.

    Возвращает путь к сохранённому исходному файлу D2.
    """
    source = source_path(output)
    with open(source, "w", encoding="utf-8") as handle:
        handle.write(d2_text)
    command = [D2_BINARY, source, output]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as err:
        raise RenderError(
            f"программа {D2_BINARY} не найдена; установите D2 "
            "(https://d2lang.com), D2-файл сохранён: " + source
        ) from err
    except subprocess.CalledProcessError as err:
        raise RenderError(f"ошибка d2: {err.stderr.strip()}") from err
    return source