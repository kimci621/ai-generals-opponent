# План 1: своя сборка движка и полигон ИИ против ИИ

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** собрать GeneralsX 1.0.4 из исходников отдельным `.app` и сделать полигон: одна команда запускает серию матчей ИИ против ИИ без окна, параллельно, и пишет результаты в CSV.

**Architecture:** в движок добавляется режим `-aiMatch` по образцу существующей симуляции повторов (`ReplaySimulation`): программно собирает `SkirmishGameInfo` из флагов, крутит логику без рендера и без ограничения FPS, на конце матча пишет JSON с результатом и выходит. Снаружи - Python-пакет `lab` (только стандартная библиотека): готовит копии данных под варианты ИИ (APFS-клоны), запускает каждый матч с отдельной песочницей `HOME`, собирает результаты.

**Tech Stack:** C++ (GeneralsX, CMake + Ninja + vcpkg, Apple clang), Python 3.14 stdlib (`subprocess`, `concurrent.futures`, `threading`, `json`, `csv`, `unittest`).

**Spec:** `~/Games/Generals/ai-lab/docs/2026-11-06-human-like-gla-bot-design.md`, шаги 0-1 раздела 6 и критерий «Полигон» раздела 7.

**Проверка плана (06.11.2026):** все ссылки на код сверены с тегом `1.0.4`, список зависимостей - с CI проекта (`.github/workflows/build-macos.yml`) и с `otool -L` официального бинарника. План прошёл независимое ревью, найденные проблемы исправлены в тексте ниже.

## Global Constraints

- Не менять: `~/Games/Generals/Generals/`, `~/Games/Generals/GeneralsZH/`, `~/Games/Generals/GeneralsXZH.app`, `~/Games/Generals/Mods/`, бутылку CrossOver, реальный профиль `~/Library/Application Support/GeneralsX/`.
- Всё новое живёт в `~/Games/Generals/ai-lab/`. Исходники движка: `ai-lab/engine/GeneralsX` (клон тега `1.0.4`), работа в ветке `ai-lab`. Своя сборка: `ai-lab/GeneralsXZH-AI.app`.
- Коммиты только локальные, без push. `ai-lab` - свой git-репозиторий, `engine/`, `data/`, `runs/`, `*.app` в `.gitignore`.
- Комментарии: в коде движка на английском с тегом `// GeneralsX @feature ai-lab DD/MM/2026 ...`, как принято в репозитории; в `lab/` на русском.
- Python: только стандартная библиотека, тесты на `unittest`, запуск `cd ~/Games/Generals/ai-lab && python3 -m unittest discover -s lab/tests -v`.
- Логика игры: 30 кадров в секунду (`LOGICFRAMES_PER_SECOND`). «2 минуты» = кадр 3600.
- Имена фракций - имена `PlayerTemplate` из INI: `FactionAmerica`, `FactionChina`, `FactionGLA`, `FactionAmericaSuperWeaponGeneral`, `FactionAmericaLaserGeneral`, `FactionAmericaAirForceGeneral`, `FactionChinaTankGeneral`, `FactionChinaInfantryGeneral`, `FactionChinaNukeGeneral`, `FactionGLAToxinGeneral`, `FactionGLADemolitionGeneral`, `FactionGLAStealthGeneral`.
- Путь карты - как в `Skirmish.ini`: `maps\alpine assault\alpine assault.map`.
- Пути к игре в скриптах выводить из расположения скрипта, не через `~`: при `HOME`-песочнице `~` указывает внутрь песочницы.
- Контрольная точка: после Task 1 (шаг 0 спецификации) остановиться и получить «да» пользователя на Tasks 2-5 (шаг 1 спецификации).

## Ограничения полигона (осознанные)

- Один процесс игры = один набор данных ИИ. В одном матче не получится свести «ванильный Hard» против «Improved AI Hard»: оба бота берут один `SkirmishScripts.scb`. Для шага 1 спецификации этого хватает, сравнение «кандидат против Improved AI» появится вместе с нашим ботом (план 2).
- Одна серия = одна карта. Несколько карт - несколько запусков серии, CSV можно склеить.

## Review Focus

1. **Зависший матч оставляет сироту.** `run.sh` запускает движок через пайплайн с `grep`. Если убить только `run.sh`, процесс `GeneralsXZH` продолжит жрать ядро. Ожидание: при таймауте убивается вся группа процессов. Тест в Task 3.
2. **Диск забивается повторами.** Каждый матч пишет `.rep` (до 11 МБ) в песочницу. 1000 матчей - это 11 ГБ. Ожидание: песочница удаляется после удачного матча и остаётся только у упавших и зависших. Тест в Task 3.
3. **Ctrl+C посреди серии.** Ожидание: за несколько секунд все запущенные движки убиты, CSV содержит завершённые матчи, прерванные в CSV не попадают. Тест и ручная проверка в Task 5.
4. **Mac засыпает ночью.** Ожидание: серия, запущенная на ночь, не встаёт. Команда серии в документации запускается через `caffeinate -is` (с `-s` Mac не спит от питания; при закрытой крышке без внешнего монитора не спасает ничто, это пишем в документации). Task 5.
5. **Полигон идёт, пока пользователь играет.** Ожидание: реальный профиль и `GeneralsZH/` не меняются, даже если параллельно запущен ярлык с Improved AI, который подменяет файлы в `GeneralsZH/`. Ручная проверка Ctrl+C не убивает игру пользователя. Варианты данных - отдельные клоны, `HOME` - песочница. Тесты в Task 2 и Task 3.

---

### Task 1: инструменты и базовая сборка без изменений

**Files:**
- Create: `ai-lab/.gitignore`, `ai-lab/README.md` (3-5 строк: что здесь лежит)
- Create: `ai-lab/scripts/build-ai-app.sh`
- Create: `ai-lab/scripts/run-ai.sh`

**Interfaces:**
- Produces: `ai-lab/GeneralsXZH-AI.app` (запуск через `Contents/MacOS/run.sh`, тот же контракт переменных `CNC_GENERALS_PATH` / `CNC_GENERALS_ZH_PATH`, что у оригинала); `scripts/run-ai.sh [args...]` - аналог `Запустить Zero Hour.command` для своей сборки.

- [x] **Step 1: поставить инструменты.** Сделано 2026-11-06, всё записано в `ai-lab/INSTALLED.md`. Спросить пользователя один раз перед установкой, это новые зависимости в системе. Список взят из CI проекта. Каждую установку отмечать в `ai-lab/INSTALLED.md` (статус `стоит`), после brew дописать туда подтянутые зависимости: `comm -13 ai-lab/baseline/brew-formula.txt <(brew list --formula -1)`. Всё, чего нет в реестре, не ставить.
  - Уже стоят (проверено 06.11.2026): `ffmpeg`, `pkgconf`, `autoconf`, `libtool`, `freetype`, `fontconfig`, `openssl@3`, `python@3.14`.
  - Поставить: `brew install cmake ninja meson autoconf-archive automake protobuf abseil glslang sdl3`. Зачем: `glslang` - DXVK компилирует им шейдеры; `sdl3` - DXVK рисует окно через SDL3 (`run.sh` ставит `DXVK_WSI_DRIVER=SDL3`), без него не работает `-win`; `protobuf` + `abseil` - сетевой модуль NGMP включён по умолчанию (`cmake/config-build.cmake:152`, `cmake/ngmp.cmake`), официальный бинарник 1.0.4 слинкован с ними; autotools - vcpkg собирает ими часть пакетов.
  - **Не ставить `glm` из Homebrew.** CI прямо запрещает: конфликт целей `glm::glm` с vcpkg. Вики проекта здесь устарела.
  - vcpkg: полный клон, не `--depth 1` (в `vcpkg.json` закреплён `builtin-baseline`, ему нужна история): `git clone https://github.com/microsoft/vcpkg ~/vcpkg && ~/vcpkg/bootstrap-vcpkg.sh -disableMetrics`.
  - Vulkan SDK: версия, на которой собирает CI, `1.4.341.1`. Скачать `https://sdk.lunarg.com/sdk/download/1.4.341.1/mac/vulkansdk-macos-1.4.341.1.zip` в пустую папку во временной директории, сверить `shasum -a 256` с `632cbe96c8ed6ed00c6ce25e3a7738c466134f76586e1c51f1419410d7f9042e`, распаковать и поставить без окна, как CI: `<распаковка>/*.app/Contents/MacOS/vulkansdk-macOS-1.4.341.1 --root ~/VulkanSDK/1.4.341.1 --accept-licenses --default-answer --confirm-command install`. Если установщик попросит пароль или не запустится, отдать пользователю: запустить `.app` двойным кликом, путь оставить `~/VulkanSDK/1.4.341.1`.
  Проверка: `ls ~/VulkanSDK/*/macOS/lib/libvulkan.dylib ~/VulkanSDK/*/macOS/lib/libMoltenVK.dylib` выводит два файла; `cmake --version`, `ninja --version`, `meson --version`, `glslangValidator --version`, `test -f ~/vcpkg/vcpkg`, `test -d /opt/homebrew/opt/protobuf`, `test -d /opt/homebrew/opt/sdl3` проходят без ошибок.
- [x] **Step 2: ветка и сборка.** Сделано 2026-11-06, сборка 3:40. `cd ai-lab/engine/GeneralsX && git switch -c ai-lab`. Из корня движка (скрипт использует относительные `build/` и `logs/`): `VCPKG_ROOT=~/vcpkg VCPKG_DEFAULT_TRIPLET=arm64-osx VULKAN_SDK=~/VulkanSDK/1.4.341.1/macOS OPENSSL_ROOT_DIR="$(brew --prefix openssl@3)" ./scripts/build/macos/build-macos-zh.sh`. Без `VULKAN_SDK` конфигурация падает: `Could NOT find Vulkan (missing: Vulkan_LIBRARY Vulkan_INCLUDE_DIR MoltenVK)`, переменные взяты из CI (`.github/workflows/build-macos.yml`). Те же переменные нужны в `scripts/build-ai-app.sh` (Step 3). Первый раз долго: vcpkg собирает зависимости, DXVK собирается через Meson. Скрипт ничего не копирует в `~/GeneralsX`, это делает только `deploy-macos-zh.sh`, его не запускаем.
  Проверка: файл `build/macos-vulkan/GeneralsMD/GeneralsXZH` существует.
- [x] **Step 3: `scripts/build-ai-app.sh`.** Сделано 2026-11-06: пересборка и упаковка 18 с, `.app` 79 МБ. От оригинала отличается только версиями библиотек ffmpeg и OpenSSL из Homebrew. Из корня движка вызывает `scripts/build/macos/build-macos-zh.sh --build-only` (полную сборку, если нет `build/macos-vulkan/CMakeCache.txt`), затем `scripts/build/macos/bundle-macos-zh.sh`, распаковывает `GeneralsXZH.app` из `<движок>/macos-arm64-GeneralsXZH.zip` во временную папку, кладёт как `ai-lab/GeneralsXZH-AI.app` (старую удаляет), сам zip удаляет. Плюс один раз добавить `macos-arm64-GeneralsXZH.zip` в `.git/info/exclude` движка.
- [x] **Step 4: `scripts/run-ai.sh`.** Сделано 2026-11-06. `ROOT` = корень установки, вычисленный от расположения скрипта (`ai-lab/scripts/` → два уровня вверх). `CNC_GENERALS_PATH=${CNC_GENERALS_PATH:-$ROOT/Generals}`, `CNC_GENERALS_ZH_PATH=${CNC_GENERALS_ZH_PATH:-$ROOT/GeneralsZH}`, `exec "$ROOT/ai-lab/GeneralsXZH-AI.app/Contents/MacOS/run.sh" "$@"`.
- [x] **Step 5: проверить, что сборка ведёт себя как оригинал.** Сделано 2026-11-06, обе проверки в песочнице с `HOME=<tmp>/home` (копия профиля), настоящий профиль не тронут. Меню: оригинал и своя сборка доходят до `entering main loop` (2 с и 7 с) и по `SIGTERM` выходят с `Exiting with code 0`, логи по 2164 строки. Повтор `00000000.rep` (перезаписан партией 20:51, 10 с игрового времени): на данных с модом обе сборки дают `CRC Mismatch in Frame 100` с одинаковыми `inGame=0xC5E5C2E4 replay=0xCC21B92C`, значит партия шла на ванильном ИИ; на ванильных данных обе доигрывают повтор, `Exiting with code 0`. Выход из меню без кликов: `pkill -TERM -f 'Resources/bin/GeneralsXZH'`, SDL превращает сигнал в обычный выход. `timeout` в macOS нет, не ставить coreutils ради него.
  Run: `scripts/run-ai.sh -win > <tmp>/ai-win.log 2>&1` и выйти из меню. Expected: в логе `entering main loop`, при выходе `Exiting with code 0`.
  Run: повтор `~/Library/Application Support/GeneralsX/GeneralsZH/Replays/00000000.rep` скопировать в `<tmp>/home/Library/Application Support/GeneralsX/GeneralsZH/Replays/`. Данные с модом: временный APFS-клон `cp -cR ~/Games/Generals/GeneralsZH <tmp>/zh && cp -R ~/Games/Generals/Mods/ImprovedAI_1.2/Data/. <tmp>/zh/Data/` (не ярлык с модом: он подменяет файлы в самой `GeneralsZH/`). Запустить `-headless -replay 00000000.rep` на оригинальном `.app` и на своём, оба с `HOME=<tmp>/home`, `CNC_GENERALS_PATH=$HOME_REAL/Games/Generals/Generals` (абсолютный путь), `CNC_GENERALS_ZH_PATH=<tmp>/zh`. Без явных переменных `run.sh` оригинала ищет игру в `$HOME/GeneralsX`, то есть внутри песочницы.
  Expected: одинаковый результат (сейчас оригинал даёт `CRC Mismatch in Frame 4800`), время одного порядка. После проверки удалить `<tmp>`.
- [x] **Step 6: коммит** в `ai-lab` (`git init` при первом коммите). Сделано 2026-11-07, `9e77d8a`.: `.gitignore`, `README.md`, `scripts/`.
- [x] **Step 7: контрольная точка.** Отчёт отдан 2026-11-07: вне `ai-lab` ~4.5 ГБ, внутри ~2.4 ГБ. Ждём «да» на Tasks 2-5. Сообщить пользователю: сборка работает, сколько заняла, сколько места съели vcpkg и `build/`. Дождаться «да» на Tasks 2-5.

### Task 2: варианты данных

**Files:**
- Create: `ai-lab/lab/__init__.py`, `ai-lab/lab/variants.py`
- Test: `ai-lab/lab/tests/test_variants.py`

**Interfaces:**
- Produces: `ensure_variant(name: str, root: Path) -> Path`. `root` - корень установки (`~/Games/Generals`). Возвращает `root/ai-lab/data/<name>`, готовую папку данных Zero Hour. `VARIANTS: dict[str, Path | None]` - `"vanilla": None`, `"improved_ai": Path("Mods/ImprovedAI_1.2/Data")`.

Логика: если `data/<name>/.variant-ok` есть, вернуть путь. Иначе собрать вариант во временной папке `data/.<name>.tmp-<uuid>` и переименовать в `data/<name>`:
1. `mkdir -p data/`, удалить недособранную `data/<name>` без `.variant-ok`.
2. APFS-клон `cp -cR root/GeneralsZH data/.<name>.tmp-<uuid>`. Целевой папки до `cp` не существует, иначе `cp` положит копию внутрь неё.
3. Привести к ванили: скопировать `root/Mods/vanilla_backup/SkirmishScripts.scb` в `Data/Scripts/`, удалить `Data/INI`, если есть. Делается всегда, даже если `GeneralsZH` сейчас «грязный» после ярлыка с модом.
4. Наложить оверлей варианта (`Data/` мода поверх `Data/` клона), записать `.variant-ok`.
5. `os.rename` во `data/<name>`. Если не вышло, потому что другой поток успел первым и там есть `.variant-ok`, удалить свою временную папку и вернуть готовый путь.

Вызов из нескольких потоков допустим, но `run_series` всё равно вызывает `ensure_variant` один раз до старта матчей.

- [x] **Step 1: тесты** на фальшивом `root` во временной папке (маленькие файлы вместо `.big`):
  - `test_vanilla_restores_original_scripts`: в фальшивом `GeneralsZH` лежат «модовый» `.scb` и `Data/INI/x.ini`. После `ensure_variant("vanilla", root)` содержимое `.scb` равно `vanilla_backup`, папки `Data/INI` нет.
  - `test_improved_ai_overlays_mod`: после `ensure_variant("improved_ai", root)` файлы мода на месте, остальные файлы из `GeneralsZH` тоже.
  - `test_source_untouched`: содержимое фальшивого `GeneralsZH` до и после вызова одинаковое.
  - `test_incomplete_variant_rebuilt`: папка варианта без `.variant-ok` пересобирается.
  - `test_concurrent_calls`: 6 потоков одновременно вызывают `ensure_variant("improved_ai", root)`. Все получают один путь, в нём нет вложенной папки `GeneralsZH`, есть `.variant-ok`, в `data/` не осталось `.improved_ai.tmp-*`.
  - `test_unknown_variant_raises`: `ValueError`.
- [x] **Step 2:** запустить, убедиться, что падают.
- [x] **Step 3:** реализовать `variants.py`.
- [x] **Step 4:** тесты проходят.
- [x] **Step 5: коммит.** Сделано 2026-11-07. Отступление: `ensure_variant` под `threading.Lock`, чтобы потоки серии не собирали один вариант одновременно.

### Task 3: запуск одного матча (обвязка)

**Files:**
- Create: `ai-lab/lab/match.py`
- Test: `ai-lab/lab/tests/test_match.py`, `ai-lab/lab/tests/fake_app/Contents/MacOS/run.sh` (исполняемый фейк движка)

**Interfaces:**
- Consumes: `ensure_variant` (Task 2).
- Produces:
```python
@dataclass(frozen=True)
class PlayerSpec:
    faction: str          # имя PlayerTemplate
    difficulty: str       # "easy" | "medium" | "hard"

@dataclass(frozen=True)
class MatchConfig:
    map: str
    players: tuple[PlayerSpec, ...]
    seed: int
    variant: str
    cash: int = 10000
    max_minutes: int = 90

@dataclass(frozen=True)
class MatchResult:
    config: MatchConfig
    status: str                       # "win" | "draw" | "timeout" | "hung" | "crash" | "aborted"
    winner_slot: int | None
    game_seconds: float | None
    wall_seconds: float
    structures_at_start: tuple[int | None, ...]  # по слотам, на первом игровом кадре
    structures_at_2min: tuple[int | None, ...]   # по слотам; None, если матч кончился раньше 2 минут
    final_crc: int | None
    run_dir: Path | None              # None, если песочница удалена

def engine_args(cfg: MatchConfig, result_path: Path) -> list[str]
def default_wall_timeout(cfg: MatchConfig) -> float   # max(900, cfg.max_minutes * 60)
def run_match(cfg: MatchConfig, *, root: Path, app: Path, runs_dir: Path,
              wall_timeout_s: float | None = None, keep: bool = False) -> MatchResult
def kill_all() -> None    # убить группы всех живых движков, запущенных run_match
```
- Контракт с движком (Task 4 реализует ровно его): аргументы `-headless -aiMatch -aiMap <map> -aiPlayer <Faction>:<difficulty>` (по одному на игрока, в порядке слотов) `-aiSeed <n> -aiCash <n> -aiMaxMinutes <n> -aiResult <path>`. Флаг `-seed` движка не использовать: в релизной сборке его нет (`CommandLine.cpp:1354`, внутри `#if defined(RTS_DEBUG)`). Коды выхода: 0 - матч доигран (победа, ничья или лимит времени), 2 - неверные аргументы, 3 - не удалось начать (нет карты, карта не для мультиплеера, на карте меньше мест, чем игроков, неизвестная фракция). JSON результата:
```json
{"schema": 1, "seed": 7, "map": "maps\\alpine assault\\alpine assault.map",
 "outcome": "win", "end_frame": 54321, "game_seconds": 1810.7, "final_crc": 2882400001,
 "players": [{"slot": 0, "faction": "FactionGLA", "difficulty": "hard", "won": true,
              "structures_at_start": 1, "structures_at_2min": 5},
             {"slot": 1, "faction": "FactionAmerica", "difficulty": "hard", "won": false,
              "structures_at_start": 1, "structures_at_2min": 6}]}
```
  `outcome`: `"win"` - ровно один `won: true`; `"draw"` - конец матча без победителя (все погибли на одном кадре), все `won: false`; `"timeout"` - сработал `-aiMaxMinutes`, все `won: false`. `structures_at_2min: null`, если до кадра 3600 не дошли.

Поведение `run_match`:
- Создаёт `runs_dir/<seed>-<uuid>/` с `home/` внутри. Окружение: `HOME=<run>/home`, `CNC_GENERALS_PATH=root/Generals`, `CNC_GENERALS_ZH_PATH=ensure_variant(cfg.variant, root)`.
- Запуск `app/Contents/MacOS/run.sh` с `engine_args(...)`, вывод в `<run>/log.txt`, `start_new_session=True`. `Popen` регистрируется в модульном реестре под `threading.Lock` и снимается с учёта после завершения.
- `wall_timeout_s=None` → `default_wall_timeout(cfg)`. По таймауту `os.killpg(..., SIGKILL)` на всю группу, статус `hung`.
- `kill_all()` убивает группы всех зарегистрированных процессов и ставит флаг; матч, убитый так, получает статус `aborted`.
- Нет JSON или ненулевой код выхода - `crash`. Иначе статус - `outcome` из JSON.
- При `win`/`draw`/`timeout` и `keep=False` папка запуска удаляется, `run_dir=None`.

- [x] **Step 1: фейк движка.** `fake_app/Contents/MacOS/run.sh` читает `-aiResult`, по переменной окружения `FAKE_MODE` пишет корректный JSON (`win`, `draw`, `timeout`), выходит с кодом 1 без файла (`crash`) или запускает дочерний `sleep 600` с маркером в командной строке и сам спит (`hang`). Ещё фейк пишет файл `$HOME/Library/Application Support/GeneralsX/touched`, чтобы проверить песочницу.
- [x] **Step 2: тесты:**
  - `test_engine_args`: для двух игроков список содержит `-aiPlayer FactionGLA:hard`, `-aiPlayer FactionAmerica:hard` в порядке слотов, `-aiSeed 7`, `-aiMap` с путём как есть (с пробелами и `\`), `-headless`, `-aiMatch`; `-seed` в списке нет.
  - `test_win_parsed`: `status == "win"`, `winner_slot == 0`, `structures_at_start == (1, 1)`, `structures_at_2min == (5, 6)`, `final_crc` - число, `run_dir is None`.
  - `test_draw_parsed`: `status == "draw"`, `winner_slot is None`.
  - `test_crash_keeps_run_dir`: `status == "crash"`, `run_dir` существует, внутри `log.txt`.
  - `test_hang_kills_process_group`: `wall_timeout_s=2`, `status == "hung"`, после возврата `pgrep -f <маркер>` пуст.
  - `test_kill_all_aborts`: `FAKE_MODE=hang`, `run_match` в отдельном потоке, через 1 с `kill_all()`. Поток завершается за 3 с, `status == "aborted"`, `pgrep -f <маркер>` пуст.
  - `test_home_is_sandboxed`: `keep=True`, файл `touched` лежит в `run_dir/home/Library/Application Support/GeneralsX/`.
  - `test_default_wall_timeout`: `max_minutes=10` → 900; `max_minutes=90` → 5400.
  - Для тестов `root` - фальшивый корень из Task 2, `app` - `fake_app`.
- [x] **Step 3:** тесты падают.
- [x] **Step 4:** реализовать `match.py`.
- [x] **Step 5:** тесты проходят.
- [x] **Step 6: коммит.** Сделано 2026-11-07.

### Task 4: режим `-aiMatch` в движке

**Files:**
- Create: `ai-lab/engine/GeneralsX/Core/GameEngine/Include/Common/AIMatch.h`, `.../Core/GameEngine/Source/Common/AIMatch.cpp`
- Modify: `Core/GameEngine/CMakeLists.txt` (рядом с `ReplaySimulation.h/.cpp`, строки ~105 и ~638)
- Modify: `Core/GameEngine/Source/Common/CommandLine.cpp` (таблица `paramsForEngineInit[]`, ~:1216, вне блоков `#if defined(RTS_DEBUG)`)
- Modify: `GeneralsMD/Code/GameEngine/Source/Common/GameMain.cpp:48-56` (третья ветка)
- Modify: `GeneralsMD/Code/GameEngine/Source/GameLogic/System/GameLogic.cpp:1385` (не создавать экран загрузки в режиме `-aiMatch`)
- Test: `ai-lab/lab/tests/test_engine_e2e.py` (пропускается, если нет `ai-lab/GeneralsXZH-AI.app`)

**Interfaces:**
- Consumes: контракт аргументов, кодов выхода и JSON из Task 3; `run_match` для e2e-тестов.
- Produces (C++):
```cpp
struct AIMatchOptions {
    Bool enabled = FALSE;
    AsciiString map;
    std::vector<AsciiString> players;   // "FactionGLA:hard"
    Int seed = -1;
    Int cash = 10000;
    Int maxMinutes = 90;
    AsciiString resultPath;
};
extern AIMatchOptions TheAIMatchOptions;
namespace AIMatch { int run(); }   // код выхода процесса
```
Seed: `-aiSeed`; без него `GetTickCount()`. Seed уходит и в `TheSkirmishGameInfo->setSeed(seed)` (как в `reallyDoStart`, `SkirmishGameOptionsMenu.cpp:476`, иначе заголовок повтора получит другой seed), и в `InitRandom(seed)`. В JSON пишется фактический seed.

Что известно из разведки (номера строк - тег 1.0.4, проверены ревью):
- Флаги из `paramsForEngineInit` разбираются внутри `TheGameEngine->init()` (`GameEngine.cpp:584`), до ветки в `GameMain`. Повторяющийся `-aiPlayer` работает: парсер проходит по всем аргументам. `-headless` - стартовый флаг.
- Образец цикла без окна и без ограничения FPS: `ReplaySimulation::simulateReplaysInThisProcess`, `Core/GameEngine/Source/Common/ReplaySimulation.cpp:86-139`: `TheGameClient->updateHeadless(); TheGameLogic->UPDATE();`.
- Сборка `GameInfo` - по образцу `SkirmishGameOptionsMenuInit()` (`SkirmishGameOptionsMenu.cpp:1308-1320`): `TheSkirmishGameInfo = NEW SkirmishGameInfo; init(); clearSlotList(); reset(); setLocalIP(getSlot(0)->getIP()); enterGame();`. Без `enterGame()` падает проверка `m_inGame` в `startGame` (`GameInfo.cpp:415-420`) и не работает `getLocalSlotNum` (:478-483).
- Слоты: сначала `GameSlot::setState(SLOT_*_AI)`, он сбрасывает цвет, позицию, шаблон и команду при переходе в ИИ (`GameInfo.cpp:203-212`), потом `setPlayerTemplate`, `setColor(-1)`, `setStartPos(-1)`, `setTeamNumber(-1)`. Сложность: easy→`SLOT_EASY_AI`, medium→`SLOT_MED_AI`, hard→`SLOT_BRUTAL_AI`. Остальные слоты `SLOT_CLOSED`. Индекс фракции: `ThePlayerTemplateStore->getTemplateNumByName`, -1 при промахе (`PlayerTemplate.cpp:290`) → код 3.
- Карта: `TheMapCache` строится при инициализации и без окна (`GameEngine.cpp:832-833`), `findMap` нормализует регистр и слэши, находит карты внутри `.big`. Нет карты, `!m_isMultiplayer` или `m_numPlayers` меньше числа игроков → код 3. Из найденной записи: `setMap`, `setMapCRC`, `setMapSize`; плюс `setStartingCash(cash)`. Потом `TheWritableGlobalData->m_mapName = getMap()`, `startGame(0)`, `setSeed`, `InitRandom(seed)`.
- `MSG_NEW_GAME` (`GAME_SKIRMISH, DIFFICULTY_NORMAL, 0`) кладётся в `TheCommandList`, а не в `TheMessageStream`: цикл без окна сообщения из `TheMessageStream` не разбирает (так делает `RecorderClass::playbackFile`, `Recorder.cpp:1340-1356`). Двойной отправки не будет: `TheCommandList` чистится в конце каждого кадра (`GameLogic.cpp:4120`); старт игры происходит на следующем `update()` (`GameLogic.cpp:3907`).
- Экран загрузки пропускается только для режима повтора (`GameLogic.cpp:1385`). Наш режим - запись, поэтому добавить в условие `&& !TheAIMatchOptions.enabled`. Это же отключает цикл затухания на :2339, он завязан на `m_loadScreen`.
- Людей среди игроков нет. Локальным становится скрытый `ReplayObserver`, `VictoryConditions` работает в режиме наблюдателя (`VictoryConditions.cpp:345-389`). `TheRecorder->isMultiplayer()` истинно для схватки (`Recorder.cpp:1912-1920`). `isSandbox()` вызывается только с экрана счёта, сюда не доходим.
- Конец матча: после каждого `UPDATE()` проверять `TheVictoryConditions->getEndFrame() != 0`; победители - игроки с `hasAchievedVictory(p)`, никого - `outcome: "draw"`. Выйти из цикла самому: `exitGame()` шлёт сообщение в `TheMessageStream`, которое здесь не разбирается.
- Лимит: кадр `maxMinutes*60*LOGICFRAMES_PER_SECOND` - `outcome: "timeout"`.
- Счёт построек: обход `TheGameLogic->getFirstObject()` / `obj->getNextObject()`, `isKindOf(KINDOF_STRUCTURE)`, `getControllingPlayer()`; игрок слота - `ThePlayerList->getPlayerFromSlotIndex(i)` (`PlayerList.h:162`). Считать на первом игровом кадре (`structures_at_start`) и на кадре 3600 (`structures_at_2min`).
- `final_crc`: `TheGameLogic->getCRC(CRC_RECALC)` на последнем кадре.
- JSON пишется атомарно: во временный файл рядом, `fflush`, потом `rename`. После этого `fflush(stdout/stderr)` и `_exit(code)`, без разбора движка: выход из загруженной записанной схватки никто не проверял, а падение на выходе превратило бы доигранный матч в `crash`. `_exit` уже используется в `SDL3Main.cpp:394`.
- Повтор матча движок пишет сам (`Recorder.cpp:451-475`). Отключать не нужно, песочница всё равно удаляется.
- Параллельные процессы движка допустимы: защита от второго экземпляра на macOS - пустая заглушка (`windows_compat.h:238`).

- [x] **Step 1: e2e-тесты** (`run_match` с настоящим `.app`, вариант `vanilla`, карта `maps\alpine assault\alpine assault.map`, `FactionGLA:hard` против `FactionAmerica:hard`). Таймаут берётся из переменной окружения `AI_E2E_TIMEOUT`, по умолчанию `default_wall_timeout`:
  - `test_match_finishes`: `seed=1`, `keep=True`, `status in ("win", "draw", "timeout")`; при `win` ровно один `won`; `game_seconds > 0`; в `result.json` поле `seed == 1`.
  - `test_ai_builds_in_first_2min`: в том же результате у каждого слота `structures_at_2min > structures_at_start` (ванильный Hard строится в первые 2 минуты; командный центр есть у всех с нулевого кадра, поэтому сравниваем с началом).
  - `test_timeout`: `max_minutes=1` - `status == "timeout"`, `59 <= game_seconds <= 61`, `structures_at_2min == (None, None)`.
  - `test_bad_faction_exit_3`: `FactionNope:hard` - `status == "crash"`, в `log.txt` строка `[AIMatch] error: unknown faction 'FactionNope'`. Все ошибки `AIMatch` печатает в stderr с префиксом `[AIMatch] error: ` и выходит с кодом из контракта.
  - `test_deterministic`: два запуска с `seed=5` и `max_minutes=10` дают одинаковые `final_crc`, `game_seconds`, `winner_slot`, `structures_at_2min`.
- [x] **Step 2:** собрать без изменений и запустить только `test_bad_faction_exit_3` с `AI_E2E_TIMEOUT=60`. Expected: `status == "hung"` (движок не знает флаги и висит в обычном цикле). Все пять тестов на старой сборке не гонять: каждый ждал бы полный таймаут.
- [x] **Step 3:** `AIMatch.h/.cpp`, обработчики флагов, правка `GameLogic.cpp:1385`, ветка в `GameMain.cpp` (`if (TheAIMatchOptions.enabled) exitcode = AIMatch::run();`). `-aiMatch` без `-headless` - код 2 и сообщение в stderr.
- [x] **Step 4:** `scripts/build-ai-app.sh`, тесты проходят.
  Если падает только `test_deterministic`, не подгонять: остановиться и сообщить пользователю с цифрами. Сначала проверить в `result.json` обоих запусков, что `seed` одинаковый и равен 5. Если seed совпал, а `final_crc` разный, движок не детерминирован, а от этого зависит, можно ли воспроизводить матчи. Решать пользователю.
- [x] **Step 5:** проверить, что обычная игра не сломалась: `scripts/run-ai.sh -win`, в логе `entering main loop`, схватка из меню запускается и показывает экран загрузки.
  Сделано частично: своя сборка доходит до `entering main loop` и выходит с кодом 0. Схватку из меню проверил пользователь 2026-11-07: партия стартовала, 30 с игры без проблем. Флаги `-ai*` добавлены в стартовую таблицу `paramsForStartup` после `-replay`.
- [x] **Step 6: коммит** в ветку `ai-lab` движка и в `ai-lab` (тест).

### Task 5: серия матчей, CSV и документация

**Files:**
- Create: `ai-lab/lab/series.py`
- Test: `ai-lab/lab/tests/test_series.py`
- Modify: `~/Games/Generals/AGENTS.md`, `~/Games/Generals/ИНСТРУКЦИЯ.md`, `ai-lab/README.md`, `~/Games/Generals/.claude/skills/zh-ai-improve/SKILL.md`

**Interfaces:**
- Consumes: `MatchConfig`, `PlayerSpec`, `run_match`, `kill_all`, `default_wall_timeout` (Task 3); `ensure_variant` (Task 2).
- Produces:
```python
CSV_COLUMNS = ["seed", "variant", "map", "factions", "difficulties", "status",
               "winner_slot", "winner_faction", "game_seconds", "wall_seconds",
               "structures_at_start", "structures_at_2min", "final_crc", "run_dir"]
def make_configs(map: str, players: tuple[PlayerSpec, ...], variant: str,
                 matches: int, first_seed: int = 1, swap_slots: bool = True,
                 max_minutes: int = 90) -> list[MatchConfig]
def run_series(cfgs: list[MatchConfig], *, root: Path, app: Path, out_csv: Path,
               jobs: int, wall_timeout_s: float | None = None) -> list[MatchResult]
```
CLI: `python3 -m lab.series --variant improved_ai --map "maps\alpine assault\alpine assault.map" --player FactionGLA:hard --player FactionAmerica:hard --matches 30 --jobs 6 --out runs/<имя>/results.csv`. Пути `root` и `app` по умолчанию вычисляются от расположения пакета: корень установки и `ai-lab/GeneralsXZH-AI.app`.

- `run_series` до старта матчей вызывает `ensure_variant` для каждого варианта из `cfgs`.
- `swap_slots=True`: в нечётных матчах игроки меняются слотами, чтобы слот не давал перекоса.
- В CSV списки через `|`. Строка дописывается и сбрасывается на диск сразу после каждого матча. Матчи со статусом `aborted` в CSV не пишутся.
- В конце печатается сводка: матчей, доля побед по фракциям, сколько `draw`/`timeout`/`hung`/`crash`, среднее `game_seconds`, сколько матчей в час.
- Ctrl+C (`KeyboardInterrupt` в главном потоке): `kill_all()`, `executor.shutdown(cancel_futures=True)`, выход с кодом 130. Ожидание - секунды, а не таймаут матча.

- [x] **Step 1: тесты** (с `fake_app` из Task 3):
  - `test_make_configs_swaps_slots`: 4 матча - seeds 1..4, во 2-м и 4-м порядок игроков обратный.
  - `test_csv_written_incrementally`: серия из 3 фейковых матчей, `jobs=2` - в CSV заголовок `CSV_COLUMNS` и 3 строки, `winner_faction` правильно взят по `winner_slot` с учётом перестановки.
  - `test_failed_matches_recorded`: с `FAKE_MODE=crash` строки есть, `status == "crash"`, `run_dir` не пуст.
  - `test_interrupt_kills_all`: серия из 4 матчей `FAKE_MODE=hang`, `jobs=2`, запуск CLI подпроцессом, через 2 с `SIGINT`. Процесс выходит с кодом 130 за 5 с, `pgrep -f <маркер>` пуст, в CSV только заголовок.
- [x] **Step 2:** тесты падают. **Step 3:** реализовать. **Step 4:** тесты проходят.
- [x] **Step 5: ручная проверка Ctrl+C:** запустить серию на 8 матчей настоящим движком, через 20 секунд нажать Ctrl+C. Expected: `pgrep -f GeneralsXZH-AI` пуст (именно `-AI`: просто `GeneralsXZH` совпадёт и с игрой пользователя), CSV читается.
- [x] **Step 6: замер запуска.** Время от старта процесса до первого игрового кадра в свежей песочнице. Если больше 15 с (холодный кэш fontconfig в каждом новом `HOME`), передавать движку `XDG_CACHE_HOME=<runs_dir>/.cache` и замерить снова.
- [x] **Step 7: приёмка полигона (критерий из спецификации):**
  Run: `caffeinate -is python3 -m lab.series --variant improved_ai --map "maps\alpine assault\alpine assault.map" --player FactionGLA:hard --player FactionAmerica:hard --matches 30 --jobs 6 --out runs/acceptance/results.csv`
  Expected: 30 строк, ни одного `hung`. Записать в `ai-lab/README.md` замеры: матчей в час, среднее время матча, сколько `jobs` тянет Mac без деградации (попробовать 4, 6, 8 на 12 матчах).
- [x] **Step 8: документация.** `AGENTS.md`: раздел про `ai-lab` (своя сборка и как пересобрать, режим `-aiMatch` и его флаги, полигон, песочница `HOME`, варианты данных, ограничения: один вариант на процесс, одна карта на серию). `ИНСТРУКЦИЯ.md`: 3-5 строк, как запустить серию на ночь (`caffeinate -is`, крышку не закрывать). В скилле `zh-ai-improve`: этап 1 сделан, где лежит.
- [x] **Step 9: коммит.** Сделано 2026-11-07. Итог Task 5: Ctrl+C (проверен на 40 матчах: серия из 8 успевала доиграть до сигнала) завершает серию с кодом 130 за доли секунды, движков не остаётся. Для этого `series.main` явно ставит обработчик SIGINT: фоновый запуск из shell его игнорирует. Запуск матча до первого кадра меньше 3 с, `XDG_CACHE_HOME` не понадобился (кэш fontconfig общий, `ai-lab/var`). Приёмка: 30 матчей на 6 потоках за 170 с, все `win`, 0 `hung`, все боты строились в первые 2 минуты. Замеры потоков в `README.md`.
