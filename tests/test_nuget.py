"""Тесты читателя метаданных NuGet (сеть заменена подделкой)."""

import unittest

from depgraph.errors import RepositoryError
from depgraph.nuget import (
    NuGetRepository,
    direct_dependencies,
    find_registration_base,
    parse_range,
    pick_version,
    version_key,
)

INDEX_URL = "https://fake/index.json"
BASE = "https://fake/reg/"


def leaf(name, version, deps, groups=1):
    """Создать лист регистрации с заданными зависимостями."""
    items = [{"id": d, "range": r} for d, r in deps]
    return {"catalogEntry": {
        "id": name, "version": version,
        "dependencyGroups": [
            {"targetFramework": f"fw{i}", "dependencies": items}
            for i in range(groups)
        ],
    }}


def registration(leaves):
    """Обернуть листы в индекс регистрации с одной встроенной страницей."""
    return {"items": [{"items": leaves}]}


DOCUMENTS = {
    INDEX_URL: {"resources": [
        {"@type": "RegistrationsBaseUrl", "@id": "https://old/"},
        {"@type": "RegistrationsBaseUrl/3.6.0", "@id": BASE},
    ]},
    BASE + "app/index.json": registration([
        leaf("App", "1.0.0", [("Lib", "1.0.0")]),
        leaf("App", "2.0.0", [("Lib", "[1.5.0, )"), ("Core", "1.0.0")],
             groups=2),
    ]),
    BASE + "lib/index.json": registration([
        leaf("Lib", "1.0.0", [("Core", "1.0.0")]),
        leaf("Lib", "1.5.0", []),
        leaf("Lib", "2.0.0", []),
    ]),
    BASE + "core/index.json": {"items": [{"@id": "https://fake/page1"}]},
    "https://fake/page1": {"items": [leaf("Core", "1.0.0", [])]},
}


def fake_fetch(url):
    """Вернуть заготовленный документ или завершиться ошибкой, как при реальной загрузке."""
    if url not in DOCUMENTS:
        raise RepositoryError(f"{url}: HTTP 404")
    return DOCUMENTS[url]


class NuGetTest(unittest.TestCase):
    """Поведение читателя репозитория NuGet."""

    def setUp(self):
        """Создать репозиторий поверх поддельных документов."""
        self.repo = NuGetRepository(INDEX_URL, fake_fetch)

    def test_registration_base_prefers_semver2(self):
        """Предпочитается ресурс регистрации 3.6.0."""
        self.assertEqual(find_registration_base(DOCUMENTS[INDEX_URL]), BASE)

    def test_direct_dependencies(self):
        """Зависимости заданной версии возвращаются с диапазонами."""
        deps = self.repo.direct_dependencies("App", "2.0.0")
        self.assertEqual(deps, {"Lib": "[1.5.0, )", "Core": "1.0.0"})

    def test_groups_are_merged(self):
        """Одна и та же зависимость в нескольких группах сообщается один раз."""
        entry = DOCUMENTS[BASE + "app/index.json"]["items"][0]["items"][1]
        self.assertEqual(len(direct_dependencies(entry["catalogEntry"])), 2)

    def test_unknown_version(self):
        """Отсутствующая версия сообщается как ошибка."""
        with self.assertRaises(RepositoryError):
            self.repo.direct_dependencies("App", "9.9.9")

    def test_unknown_package(self):
        """Отсутствующий пакет сообщается как ошибка."""
        with self.assertRaises(RepositoryError):
            self.repo.direct_dependencies("Nope", "1.0.0")

    def test_paged_registration(self):
        """Страницы регистрации без встроенных элементов загружаются."""
        self.assertEqual(self.repo.direct_dependencies("Core", "1.0"), {})

    def test_dependencies_resolve_versions(self):
        """Версии зависимостей выбираются из их диапазонов."""
        self.repo.set_version("App", "2.0.0")
        self.assertEqual(self.repo.dependencies("App"), ["Lib", "Core"])
        self.assertEqual(self.repo.dependencies("Lib"), [])

    def test_range_parsing(self):
        """Разбираются нижние границы диапазонов NuGet."""
        self.assertEqual(parse_range("1.0"), ("1.0", True))
        self.assertEqual(parse_range("[1.0, 2.0)"), ("1.0", True))
        self.assertEqual(parse_range("(1.0, )"), ("1.0", False))
        self.assertEqual(parse_range("(, 2.0]"), (None, False))

    def test_pick_version(self):
        """Выбирается наименьшая подходящая версия."""
        versions = ["2.0.0", "1.0.0", "1.5.0"]
        self.assertEqual(pick_version("1.2", versions), "1.5.0")
        self.assertEqual(pick_version("(1.0.0, )", versions), "1.5.0")
        self.assertEqual(pick_version("(, 2.0]", versions), "2.0.0")

    def test_version_order(self):
        """Предварительные версии сортируются перед релизом."""
        self.assertLess(version_key("1.0.0-beta"), version_key("1.0.0"))
        self.assertLess(version_key("1.0.0-beta.2"),
                        version_key("1.0.0-beta.10"))
        self.assertEqual(version_key("1.0"), version_key("1.0.0.0"))


if __name__ == "__main__":
    unittest.main()