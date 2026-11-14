"""Чтение метаданных пакета из репозитория NuGet v3."""

import gzip
import json
import urllib.error
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

from depgraph.errors import RepositoryError

REGISTRATION_TYPE = "RegistrationsBaseUrl"
PREFERRED_REGISTRATION_TYPE = "RegistrationsBaseUrl/3.6.0"
GZIP_MAGIC = b"\x1f\x8b"
REQUEST_TIMEOUT = 30
VERSION_PARTS = 4
RELEASE_RANK = 1
PRERELEASE_RANK = 0
NUMERIC_RANK = 0
TEXT_RANK = 1

Fetcher = Callable[[str], dict]


def fetch_json(url: str) -> dict:
    """Скачать документ JSON, распаковывая gzip-данные при необходимости."""
    request = urllib.request.Request(
        url, headers={"Accept-Encoding": "gzip"}
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read()
    except urllib.error.HTTPError as err:
        raise RepositoryError(f"{url}: HTTP {err.code}") from err
    except (urllib.error.URLError, OSError) as err:
        raise RepositoryError(f"{url}: {err}") from err
    if data.startswith(GZIP_MAGIC):
        data = gzip.decompress(data)
    try:
        return json.loads(data)
    except ValueError as err:
        raise RepositoryError(f"{url}: некорректный JSON") from err


def find_registration_base(index: dict) -> str:
    """Вернуть базовый URL регистраций пакетов из индекса сервиса."""
    found = {
        res.get("@type"): res.get("@id")
        for res in index.get("resources", [])
        if isinstance(res, dict)
    }
    for kind in (PREFERRED_REGISTRATION_TYPE, REGISTRATION_TYPE):
        if kind in found:
            return found[kind]
    raise RepositoryError("в индексе сервиса нет ресурса RegistrationsBaseUrl")


def collect_entries(registration: dict, fetch: Fetcher) -> List[dict]:
    """Собрать записи каталога всех версий из регистрации."""
    entries = []
    for page in registration.get("items", []):
        if "items" not in page:
            page = fetch(page["@id"])
        for leaf in page.get("items", []):
            entry = leaf.get("catalogEntry")
            if isinstance(entry, dict):
                entries.append(entry)
    return entries


def _identifier_key(identifier: str) -> Tuple[int, object]:
    """Ключ сортировки одного идентификатора предварительной версии."""
    if identifier.isdigit():
        return (NUMERIC_RANK, int(identifier))
    return (TEXT_RANK, identifier)


def version_key(version: str) -> tuple:
    """Вернуть ключ, упорядочивающий версии согласно SemVer."""
    base = version.split("+")[0]
    core, _, pre = base.partition("-")
    numbers = [int(p) if p.isdigit() else 0 for p in core.split(".")]
    numbers += [0] * (VERSION_PARTS - len(numbers))
    if not pre:
        return (tuple(numbers), RELEASE_RANK, ())
    ids = tuple(_identifier_key(p) for p in pre.split("."))
    return (tuple(numbers), PRERELEASE_RANK, ids)


def find_entry(entries: List[dict], version: str) -> Optional[dict]:
    """Найти запись каталога, версия которой в точности совпадает с заданной."""
    wanted = version_key(version)
    for entry in entries:
        if version_key(entry.get("version", "")) == wanted:
            return entry
    return None


def direct_dependencies(entry: dict) -> Dict[str, str]:
    """Вернуть прямые зависимости (id -> диапазон) из всех групп целей."""
    result: Dict[str, str] = {}
    for group in entry.get("dependencyGroups", []):
        for dep in group.get("dependencies", []):
            result.setdefault(dep["id"], dep.get("range", ""))
    return result


def parse_range(text: str) -> Tuple[Optional[str], bool]:
    """Вернуть нижнюю границу диапазона NuGet и признак её включения."""
    text = text.strip()
    if not text or text[0] not in "[(":
        return (text or None), True
    lower = text[1:-1].split(",")[0].strip()
    return (lower or None), text.startswith("[")


def pick_version(range_text: str, versions: List[str]) -> str:
    """Выбрать наименьшую версию, удовлетворяющую нижней границе диапазона.

    NuGet разрешает зависимости в наименьшую подходящую версию.
    Диапазон без нижней границы разрешается в последнюю версию.
    """
    ordered = sorted(versions, key=version_key)
    lower, inclusive = parse_range(range_text)
    if lower is not None:
        bound = version_key(lower)
        for version in ordered:
            key = version_key(version)
            if key > bound or (inclusive and key == bound):
                return version
    return ordered[-1]


class NuGetRepository:
    """Источник зависимостей на основе индекса сервиса NuGet v3."""

    def __init__(self, index_url: str, fetch: Fetcher = fetch_json):
        """Сохранить данные смежности."""
        self._index_url = index_url
        self._fetch = fetch
        self._base: Optional[str] = None
        self._entries: Dict[str, List[dict]] = {}
        self._versions: Dict[str, str] = {}

    def _registration_base(self) -> str:
        """Вернуть (кэшированный) базовый URL регистраций."""
        if self._base is None:
            self._base = find_registration_base(self._fetch(self._index_url))
        return self._base

    def package_entries(self, name: str) -> List[dict]:
        """Вернуть записи каталога всех версий пакета."""
        key = name.lower()
        if key not in self._entries:
            base = self._registration_base().rstrip("/")
            registration = self._fetch(f"{base}/{key}/index.json")
            entries = collect_entries(registration, self._fetch)
            if not entries:
                raise RepositoryError(f"пакет не найден: {name}")
            self._entries[key] = entries
        return self._entries[key]

    def set_version(self, name: str, version: str) -> None:
        """Запомнить версию пакета, подлежащего анализу."""
        self._versions[name.lower()] = version

    def direct_dependencies(self, name: str, version: str) -> Dict[str, str]:
        """Вернуть прямые зависимости (id -> диапазон) версии пакета."""
        entry = find_entry(self.package_entries(name), version)
        if entry is None:
            raise RepositoryError(f"версия {version} пакета {name} не найдена")
        return direct_dependencies(entry)

    def dependencies(self, name: str) -> List[str]:
        """Вернуть имена прямых зависимостей известного пакета."""
        version = self._versions.get(name.lower())
        if version is None:
            raise RepositoryError(f"неизвестна версия пакета {name}")
        deps = self.direct_dependencies(name, version)
        for dep_id, range_text in deps.items():
            available = [e["version"] for e in self.package_entries(dep_id)]
            self._versions.setdefault(
                dep_id.lower(), pick_version(range_text, available)
            )
        return list(deps)