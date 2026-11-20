# depgraph

Инструмент визуализации графа зависимостей пакетов **NuGet** (.NET).
Зависимости читаются напрямую из репозитория NuGet v3 по HTTP:
менеджеры пакетов и сторонние библиотеки для этого не используются
(только стандартная библиотека Python 3.9+). Для отрисовки SVG нужна
отдельная программа [D2](https://d2lang.com).

## Возможности

- чтение прямых зависимостей заданной версии пакета из NuGet v3;
- построение графа с учётом транзитивности: BFS **с рекурсией**
  (каждый рекурсивный вызов обрабатывает один уровень графа);
- корректная обработка циклов (пакет раскрывается один раз);
- тестовый режим: граф берётся из текстового файла, пакеты называются
  заглавными латинскими буквами;
- вывод обратных зависимостей (кто зависит от пакета);
- генерация диаграммы на языке D2 и изображения в формате SVG.

## Параметры командной строки

| Опция | Описание |
|---|---|
| `--package` | имя анализируемого пакета (обязательно) |
| `--repo` | URL service index репозитория (`https://api.nuget.org/v3/index.json`) или путь к файлу тестового репозитория (обязательно) |
| `--repo-mode` | `remote` (по умолчанию) или `test` |
| `--version` | версия пакета; обязательна в режиме `remote`, в `test` игнорируется |
| `--output` | имя SVG-файла (по умолчанию `graph.svg`); рядом создаётся `.d2`-файл с тем же именем |
| `--show-config` | вывести параметры в формате ключ-значение (этап 1) |
| `--direct-only` | вывести только прямые зависимости (этап 2) |
| `--reverse`, `--target` | вывести обратные зависимости пакета `--target` в графе пакета `--package` (этап 4) |

Ошибки в параметрах (неверное имя пакета, URL, версия, отсутствующий файл
или каталог, не-`.svg` имя, `--reverse` без `--target` и т. д.) приводят
к сообщению и коду возврата 2. Ошибки репозитория и отрисовки — код 1.

### Формат тестового репозитория

```text
# комментарий
A: B C      # A зависит от B и C
B: C D
C: A        # циклы разрешены
D:          # нет зависимостей
```

Пакет, упомянутый только как зависимость, считается пакетом без
зависимостей. Примеры лежат в `tests/data/`.

### Как выбираются версии зависимостей

Граф строится по идентификатору пакета. Версия транзитивной зависимости
выбирается как **наименьшая версия, удовлетворяющая нижней границе диапазона** (так NuGet разрешает зависимости); для диапазона без нижней
границы берётся последняя версия. Если пакет встретился несколько раз,
используется версия, выбранная при первой встрече. Зависимости всех
целевых платформ (`dependencyGroups`) объединяются.

## Сборка, запуск и тесты

Сборка не нужна. Требуется Python 3.9+; для SVG — программа `d2`
в `PATH`.

### Запуск через Makefile

Если установлен Make, можно использовать следующие команды:

```bash
make run ARGS="--package A --repo tests/data/cycle.txt --repo-mode test"
make test
```

### Запуск без Makefile

Использовать Makefile необязательно. Все команды можно выполнять непосредственно через Python.

Перейдите в корневую директорию проекта (где находятся `Makefile`, `src` и `tests`).

**Windows (PowerShell):**

Сначала задайте переменную окружения `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "src"
```

После этого можно запускать приложение и тесты.

**Linux / macOS:**

Для каждой команды указывайте `PYTHONPATH=src`:

```bash
PYTHONPATH=src python3 -m depgraph
```

### Запуск тестов

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -t .
```

Linux / macOS:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -t .
```

## Примеры

### 1. Просмотр конфигурации (этап 1)

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m depgraph --package A --repo tests/data/cycle.txt --repo-mode test --show-config
```

Linux / macOS:

```bash
PYTHONPATH=src python3 -m depgraph --package A --repo tests/data/cycle.txt --repo-mode test --show-config
```

### 2. Реальный репозиторий, прямые зависимости (этап 2)

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m depgraph --package Microsoft.Extensions.Logging --version 8.0.0 --repo https://api.nuget.org/v3/index.json --direct-only
```

Linux / macOS:

```bash
PYTHONPATH=src python3 -m depgraph --package Microsoft.Extensions.Logging --version 8.0.0 --repo https://api.nuget.org/v3/index.json --direct-only
```

### 3. Построение полного графа и SVG (этап 5)

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m depgraph --package Microsoft.Extensions.Logging --version 8.0.0 --repo https://api.nuget.org/v3/index.json --output logging.svg
```

Linux / macOS:

```bash
PYTHONPATH=src python3 -m depgraph --package Microsoft.Extensions.Logging --version 8.0.0 --repo https://api.nuget.org/v3/index.json --output logging.svg
```

Результат:
- `logging.svg` — изображение графа;
- `logging.d2` — исходный файл диаграммы D2.

Для генерации SVG необходимо предварительно установить D2 и добавить его в `PATH`.

### 4. Тестовый репозиторий с циклом

Проверка графа `A -> B -> C -> A`, а также зависимости `D -> D`.

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m depgraph --package A --repo tests/data/cycle.txt --repo-mode test
```

Linux / macOS:

```bash
PYTHONPATH=src python3 -m depgraph --package A --repo tests/data/cycle.txt --repo-mode test
```

Пример вывода:

```text
A -> B
B -> C, D
C -> A
D -> D
D2: graph.d2
SVG: graph.svg
```

### 5. Обратные зависимости (этап 4)

Проверка того, какие пакеты зависят от `D` в графе пакета `A`.

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m depgraph --package A --repo tests/data/tree.txt --repo-mode test --reverse --target D
```

Linux / macOS:

```bash
PYTHONPATH=src python3 -m depgraph --package A --repo tests/data/tree.txt --repo-mode test --reverse --target D
```

Пример вывода:

```text
B
C
A
```
