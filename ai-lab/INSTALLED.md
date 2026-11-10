# Что поставлено для работы над ИИ

Реестр всего, что ставится в систему ради ИИ. По нему потом удаляем. Правило: сначала запись здесь, потом установка. Что стояло до начала работы, лежит в `baseline/` (снимок от 2026-11-06).

## Было до начала (не удалять)

- Homebrew-пакеты из `baseline/brew-formula.txt` и `baseline/brew-cask.txt`. Из нужных для сборки уже стоят `autoconf`, `pkgconf`, `git`, `python@3.14`.
- Xcode (`/Applications/Xcode.app`).
- Python 3.14 через pyenv, пакеты из `baseline/pip.txt`.

## Поставлено

Статусы: `план` (ещё не ставили), `стоит`, `удалено`.

### Homebrew

| Пакет | Зачем | Статус |
|---|---|---|
| cmake | сборка движка | стоит |
| ninja | сборка движка | стоит |
| meson | DXVK собирается через Meson | стоит |
| autoconf-archive | vcpkg собирает ими часть пакетов | стоит |
| automake | то же | стоит |
| protobuf | сетевой модуль NGMP, без него сборка не идёт | стоит |
| abseil | то же | стоит |
| glslang | DXVK компилирует шейдеры | стоит |
| sdl3 | окно DXVK, без него не работает `-win` | стоит |

Подтянуты зависимостями (2026-11-06): `spirv-headers`, `spirv-tools` (от glslang). Уходят сами через `brew autoremove`. Проверка списка: `comm -13 baseline/brew-formula.txt <(brew list --formula -1)`.

Пакеты Homebrew вместе с зависимостями занимают около 150 МБ.

Скачанные архивы Homebrew осели в `~/Library/Caches/Homebrew` (было 104 МБ, стало 171 МБ).

### Вне Homebrew

| Что | Где | Зачем | Статус |
|---|---|---|---|
| vcpkg (полный git-клон) | `~/vcpkg` | зависимости движка | стоит, 1.9 ГБ на 2026-11-07, из них `buildtrees` 1.3 ГБ |
| кэш пакетов vcpkg | `~/.cache/vcpkg` | создан первой сборкой, ускоряет пересборку | стоит, 125 МБ |
| Vulkan SDK 1.4.341.1 | `~/VulkanSDK` | сборка движка | стоит, 2.3 ГБ |
| кэш установщика Vulkan SDK | `~/Library/Caches/qt-installer-framework` | создан установщиком, 24 КБ | стоит |

В `/usr/local` установщик Vulkan SDK ничего не положил: до и после установки содержимое совпало (2026-11-06). В `~/Library/Preferences` и `~/Library/Application Support` следов тоже нет.

### Внутри `ai-lab/` (уходит вместе с папкой)

- `engine/GeneralsX` - клон исходников, 90 МБ, плюс `build/` 2.3 ГБ и `logs/` 46 МБ (2026-11-07).
- `engine/GeneralsX.wiki` - клон wiki.
- `GeneralsXZH-AI.app` - своя сборка, 79 МБ (2026-11-06). Все библиотеки скопированы внутрь, как в оригинальном `.app`.
- `scripts/run-ai.sh` - запуск своей сборки на данных установки. Вне `ai-lab` ничего не создаёт, кроме лога DXVK `GeneralsZH/GeneralsXZH_d3d9.log`: его перезаписывает и обычный запуск игры.
- `data/<вариант>` - данные Zero Hour под вариант ИИ (`vanilla`, `improved_ai`). Это APFS-клоны `GeneralsZH`: `du` показывает 2.2 ГБ, на диске почти ничего, место занимают только изменённые файлы.
- `runs/<серия>/` - результаты серий (`results.csv`), упавшие матчи оставляют там свою песочницу.
- `var/cache/fontconfig` - кэш шрифтов, движок пишет его в `../../var` от своей рабочей папки (`data/<вариант>`). Оригинальная игра так же создала `~/Games/var` ещё 2026-11-06 17:25, до работы над ИИ: это не наше, но и не нужное, удаляется вместе с игрой.
- `scripts/build-ai-app.sh` - пересборка. Вне `ai-lab` ничего не создаёт: временная папка упаковщика удаляется сама, zip тоже.

## Как удалить

Всё, что выше помечено `стоит`:

```sh
# Homebrew: наши пакеты, потом их осиротевшие зависимости
brew uninstall cmake ninja meson autoconf-archive automake protobuf abseil glslang sdl3
brew autoremove
# проверка: пусто = вернулись к снимку
comm -13 ~/Games/Generals/ai-lab/baseline/brew-formula.txt <(brew list --formula -1)

rm -rf ~/vcpkg ~/.cache/vcpkg ~/VulkanSDK ~/Library/Caches/qt-installer-framework
brew cleanup --prune=all   # скачанные архивы в ~/Library/Caches/Homebrew
```

Папку `ai-lab/` удалять отдельно и только если ИИ больше не нужен: в ней свой мод и полигон.
Перед удалением сверить пункты с этим списком: если сюда дописали что-то новое, удалить и его.
