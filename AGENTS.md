# AGENTS.md: C&C Generals Zero Hour на macOS

Памятка для агента: что здесь собрано, зачем и как это чинить. Инструкция для человека лежит в `ИНСТРУКЦИЯ.md`.

Машина: MacBook M4 Pro, Apple Silicon. Настроено 2026-11-04.

## Установка

Zero Hour на движке GeneralsX (порт открытых исходников EA для arm64, рендер через DXVK и MoltenVK). Без Wine. Обычный Zero Hour плюс мод ИИ.

Данные когда-то скопированы из бутылки CrossOver `1` (Rise of the Reds 1.86 поверх Zero Hour, с GenTool). Пользователь удалил бутылку 2026-11-08, CrossOver.app остался. Другого источника данных нет, папки `Generals/` и `GeneralsZH/` беречь. WorldBuilder тоже был только в бутылке, править `.scb` можно только своим конвертером.

## Структура папки

```
~/Games/Generals/
├── GeneralsXZH.app                          # GeneralsX 1.0.4, macOS arm64
├── Generals/                                # данные базовой Generals (Zero Hour без них не работает)
├── GeneralsZH/                              # данные Zero Hour без файлов RotR
├── Mods/ImprovedAI_1.2/Data/                # мод ИИ (только Hard AI)
├── Mods/ImprovedAI_Plus/                    # свой ИИ: Improved AI + правки (SkirmishScripts.txt, CHANGELOG.md)
├── Mods/vanilla_backup/SkirmishScripts.scb  # оригинальный ИИ ZH, создаётся при первом запуске мода
├── Запустить Zero Hour.command              # обычный запуск
├── Запустить Zero Hour (Improved AI).command  # запуск с модом
├── Запустить Zero Hour (Improved AI Plus).command  # запуск со своим ИИ
├── Запустить Zero Hour (Improved AI Plus, свой движок).command  # свой ИИ на сборке ai-lab
├── tools/bigx.py                            # распаковщик архивов .big
├── tools/scb.py                             # SkirmishScripts.scb <-> текст
├── ai-lab/                                  # полигон ИИ: своя сборка движка и матчи ИИ против ИИ
├── ИНСТРУКЦИЯ.md                            # для человека
└── AGENTS.md / CLAUDE.md                    # этот файл и ссылка на него
```

Источник GeneralsX: https://github.com/fbraz3/GeneralsX (релизы и wiki). Wiki удобно клонировать: `git clone --depth 1 https://github.com/fbraz3/GeneralsX.wiki.git`.

Git: вся папка - один репозиторий, ветка `master`, remote https://github.com/kimci621/ai-generals-opponent (публичный). Файлы игры, `.app`, `Mods/vanilla_backup/`, `ai-lab/engine|data|runs` в `.gitignore`. Движок не в репозитории: наши коммиты к нему лежат патчами в `ai-lab/engine-patches/` (там же как восстановить), после новых коммитов в движке патчи надо выгрузить заново. Старый отдельный `.git` полигона сохранён в `.backup/ai-lab.git`, его история перенесена в общий репозиторий.

## Как устроен запуск

- `GeneralsXZH.app/Contents/MacOS/run.sh` выставляет окружение (DYLD, MoltenVK, DXVK) и запускает `Contents/Resources/bin/GeneralsXZH`. По умолчанию данные ищет в `~/GeneralsX/Generals` и `~/GeneralsX/GeneralsZH`.
- `Запустить Zero Hour.command` задаёт `CNC_GENERALS_PATH=<папка>/Generals` и `CNC_GENERALS_ZH_PATH=<папка>/GeneralsZH`, потом делает `exec run.sh "$@"`. Поэтому `.app` напрямую не запускать: он не найдёт данные.
- `Запустить Zero Hour (Improved AI).command`: при первом запуске сохраняет оригинальный `SkirmishScripts.scb` в `Mods/vanilla_backup/`, копирует `Mods/ImprovedAI_1.2/Data/` поверх `GeneralsZH/Data/`, вызывает обычный ярлык и через `trap` (EXIT HUP INT TERM) возвращает оригинал: копирует `.scb` обратно и удаляет `GeneralsZH/Data/INI`.
- `Запустить Zero Hour (Improved AI Plus).command`: то же самое, но с `Mods/ImprovedAI_Plus/Data/`. Проверено 2026-11-09: подмена, запуск до меню и возврат ванили после выхода.
- `Запустить Zero Hour (Improved AI Plus, свой движок).command`: та же подмена, но запускает `ai-lab/scripts/run-ai.sh` (сборка `ai-lab/GeneralsXZH-AI.app` с правками движка для ИИ). Проверено 2026-11-12: меню с `-win`, `.scb` Plus на месте, после выхода ванила вернулась. Живую игру на этой сборке пользователь ещё не проверял.
- `-win` запускает в окне. Весь лог идёт в stdout/stderr.

## Пользовательские данные GeneralsX

`~/Library/Application Support/GeneralsX/GeneralsZH/`: `Options.ini` (сейчас `Resolution = 2048 1280`), `SagePatch.ini`, `Skirmish.ini`, `Replays/`, `MapPreviews/`.

Графика в `Options.ini` (2026-11-06, бэкап в `Options.ini.bak`): `TextureFilter = Anisotropic`, `AnisotropyLevel = 16`, `PostProcessFXAA = yes`, остальные ключи GeneralsX (`AdvancedLighting`, `AdvancedShadows`, `PostProcessBloom/HDR`, `ExplosionDynamicLights`, `VehicleHeadlights`, `WaterReflections` и др.) прописаны явно как `yes`, хотя в коде они и так включены по умолчанию. `StaticGameLOD = VeryHigh` - настоящий пресет GeneralsX (5000 частиц, все эффекты), не путать с `Custom`. MSAA (`AntiAliasing`) не включать: при нём движок пропускает постобработку (`[POST_PROCESS] Multisampled depth buffer cannot be paired...`), пропадут bloom и HDR. Следы гусениц на VeryHigh зашиты в коде (100 сегментов, 60 с), в `GameData`/`SagePatch.ini` их не задать.

Папка `~/Documents/Command and Conquer Generals Zero Hour Data/` осталась от CrossOver/RotR (бутылка удалена), GeneralsX её не читает.

## Что сделано и почему

1. **Данные скопированы из бутылки CrossOver** через rsync. Из `Generals ZeroHour` исключены `/!*` (все `!Rotr_*.big` и `!!!!!!ROTR_*.big`), `ROTR185_*`, `SWR*`, `WorldBuilder_ROTR.exe`, `*.cmd`, `Data/Rotr185LnchrRus`, `Data/Movies/ROTR_Intro.bik` и `d3d8.dll` (GenTool). Движок подключает все `*.big` из папки, поэтому файлы RotR превратили бы ванилу в RotR.
2. **Починен неподвижный ИИ.** Установщик мода переименовал ванильные `Data/Scripts/SkirmishScripts.scb`, `MultiplayerScripts.scb` и `Scripts.ini` в `*_scb.contra` и `Scripts_ini.contra`. Движок ищет `Data\Scripts\SkirmishScripts.scb` (проверено через `strings` по бинарнику). Не найдя его в ZH, он брал ИИ из базовой `Generals/Data/Scripts`, где нет подфракций ZH, и боты стояли. Имена в `GeneralsZH` возвращены.
3. **Мод Improved AI 1.2** (CobraThiboK, https://www.moddb.com/mods/improved-ai-for-zero-hour). Исходный архив: `~/Downloads/Improved_AI_1.2.rar`. Состав:
   - `Data/Scripts/SkirmishScripts.scb` - новый ИИ, улучшен только Hard.
   - `Data/INI/Default/AIData.ini` - параметры ИИ.
   - `Data/INI/Default/Weapon.ini` - добавлен `TunnelNetworkGunDUMMY2`, у `AmbulanceCleanHazardWeapon` радиус 50 → 20, дальность 100 → 30 (по словам автора, ИИ зависал).
   - `Data/INI/Default/CommandSet.ini` и `CommandButton.ini` - скрытые кнопки только для скриптов ИИ (`Command_ConstructAmericaVehicleChinookForDrops`, `Demo_Command_TertiarySuicide2`).
   - `Scripts.ini` и `MultiplayerScripts.scb` из архива совпадают с ванильными побайтно, поэтому не копировались.
   - Подвох: кнопка ссылается на объект `AmericaVehicleChinookForDrops`, которого нет ни в игре, ни в моде. Загрузку это не ломает, в тестовом запуске игра дошла до меню без ошибок INI.
   - В ванили `Weapon.ini`, `CommandSet.ini` и `CommandButton.ini` лежат в `Data\INI\` внутри `INIZH.big` и грузятся после `Data\INI\Default\`. Поэтому записи с теми же именами (например, скорая) могут перекрываться ванильными, а новые записи добавляются.

## Диагностика

- **Лог:** `cd ~/Games/Generals && "./Запустить Zero Hour.command" -win > /tmp/gx.log 2>&1`. Успешный старт содержит `entering main loop`, нормальный выход - `Exiting with code 0`.
- **Розовые текстуры:** в логе будут `[TEX_MISSING]` и `[ASSET_FAIL]`, значит не найдена база `Generals/`. Проверить `CNC_GENERALS_PATH` и наличие `Generals/Textures.big`. Одна строка `[TEX_MISSING] 'trstrtholecvr.tga'` была и в ванили, она безвредна.
- **Боты стоят:** проверить, что `GeneralsZH/Data/Scripts/SkirmishScripts.scb` на месте. Ванильный файл весит 2272629 байт, мод - 2295027. Нет ли снова `*.contra`: `find GeneralsZH -iname '*.contra'`.
- **Ванила осталась с модом** после аварийного выхода: если есть `GeneralsZH/Data/INI` или размер `.scb` не 2272629 (Improved AI - 2295027, Plus - другой), скопировать `Mods/vanilla_backup/SkirmishScripts.scb` в `GeneralsZH/Data/Scripts/` и удалить `GeneralsZH/Data/INI`.
- **Заглянуть в архив .big:** `python3 -I tools/bigx.py <файл.big> <папка_вывода> <подстрока_имени>...`. Без подстроки ничего не извлечёт, с `.ini` извлечёт все INI.
- **Скрипты ИИ в текст и обратно:** `python3 -I tools/scb.py dump <scb> <txt>`, `build <txt> <scb>`, `check <scb>...` (кругооборот побайтно; ванила, Improved AI и `MultiplayerScripts.scb` проходят). Формат текста описан в шапке `tools/scb.py`. Текст Improved AI около 215 тыс. строк.
- **Gatekeeper:** при блокировке `xattr -dr com.apple.quarantine GeneralsXZH.app`.

## Обновление GeneralsX

`gh release download -R fbraz3/GeneralsX -p 'macOS-GeneralsXZH.zip'`, распаковать, заменить `GeneralsXZH.app`. Данные и ярлыки не трогать. После обновления проверить, что `run.sh` всё ещё читает `CNC_GENERALS_PATH` и `CNC_GENERALS_ZH_PATH`.

## ai-lab: полигон ИИ против ИИ

Своя сборка GeneralsX с режимом матча без окна. Подробности в `ai-lab/README.md`, план в `ai-lab/docs/plans/2026-11-06-plan-1-build-and-polygon.md`.

- **Движок:** `ai-lab/engine/GeneralsX`, ветка `ai-lab`. Сборка: `ai-lab/scripts/build-ai-app.sh`, результат `ai-lab/GeneralsXZH-AI.app` (первая сборка около 4 мин, повторная около 20 с). Запуск сборки с данными этой папки: `ai-lab/scripts/run-ai.sh [-win]`. Оригинальный `GeneralsXZH.app` не трогаем.
- **Режим `-aiMatch`** (`Core/GameEngine/Source/Common/AIMatch.cpp`): `-headless -aiMatch -aiMap <карта> -aiPlayer Faction:easy|medium|hard` (по одному на слот, 2-8) `-aiSeed N -aiCash N -aiMaxMinutes N -aiResult <файл.json>`. Пишет JSON с `outcome` (`win`/`draw`/`timeout`), победителем, числом построек на старте и на 2-й минуте, итоговым CRC. С 2026-11-07 (`schema: 2`) ещё и технические здания: `derricks_on_map`/`tech_on_map` (всего на карте при старте) и у каждого игрока `derricks`/`tech_buildings` (сколько у него на 5-й, 10-й минуте и в конце; `null`, если матч кончился раньше). В CSV серии это колонки `derricks_on_map`, `derricks_5min`, `derricks_10min`, `derricks_end`, `tech_on_map`, `tech_end`. Счётчик только читает состояние, CRC не меняет. Коды выхода: 0 матч сыгран, 2 плохие аргументы, 3 не стартовал (ошибка в stderr с `[AIMatch] error:`). Одинаковый seed даёт одинаковый CRC.
- **Полигон** `ai-lab/lab/`: `python3 -m lab.series ...` из `ai-lab/` (пример в README). Каждый матч идёт в своей песочнице: `HOME=runs/<серия>/<seed>-<id>/home`, поэтому настоящий профиль GeneralsX не меняется. Удачные матчи папку удаляют, `crash`/`hung` оставляют с `log.txt`. Ctrl+C убивает все движки серии.
- **Варианты данных** `ai-lab/data/<вариант>`: APFS-клон `GeneralsZH` с наложенным модом (`vanilla`, `improved_ai`, `improved_ai_gla`, `improved_ai_plus`; список в `lab/variants.py`). После пересборки мода удалить его клон `ai-lab/data/<вариант>`, иначе полигон возьмёт старую копию. Ванила не трогается.
- **Свой `.scb` на игрока** (с 2026-11-10, `schema: 3`): `-aiPlayer Faction:hard:<путь к .scb>`. При создании игрока движок (`Player::initFromDict`) временно подменяет шаблоны скриптов и команд ИИ на загруженные из этого файла, копирует их игроку и возвращает общие. INI у всех игроков общие, от варианта матча. В полигоне это `PlayerSpec(..., scripts="<вариант>")` или `--player FactionGLA:hard:improved_ai_plus`; полигон проверяет, что варианты отличаются только `.scb`. Проверено: тот же `.scb`, данный игроку явно, даёт тот же CRC, что и без подмены; оба бота на Plus через подмену дают тот же CRC, что и вариант `improved_ai_plus` целиком. В CSV колонка `scripts`.
- **Дуэль** кандидата с соперником по критерию скилла: `python3 -m lab.duel --candidate improved_ai_plus --opponent improved_ai --per-pair 10 --jobs 6 --out runs/<имя>/results.csv` (3 карты, 9 пар сторон, слоты чередуются, 270 матчей, ~20 мин). Вердикт по готовому CSV: `--report <csv> --candidate <вариант>`.
- **Ограничения:** одна карта на серию в `lab.series` (в `lab.duel` три). Свой на игрока только `.scb`, INI общие.
- **Трейс** (только своя сборка, только чтение, CRC не меняет): `AI_LAB_TRACE=<подстрока>` пишет в stderr матча строки `[TRACE f=кадр]`. `Tech` включает владельцев техзданий раз в секунду, базы игроков, улучшение захвата и юниты команд, в имени которых есть подстрока (позиция, hp, состояние ИИ `AIStateType`, источник команды, цель). Ещё: переходы условий скриптов и запуск последовательных скриптов (подстрока в имени скрипта), `TechDistance` (условие «техздание рядом»), `MoveNearest` (выбор цели в `TEAM_MOVE_TOWARDS_NEAREST_OBJECT_TYPE` и точки зоны), `Hunt` (кандидаты и выбор цели в охоте с захватом). `ScriptErr` печатает отладочные сообщения скриптового движка (`AppendDebugMessage`): шаги последовательных скриптов и ошибки вроде «у юнита нет кнопки для охоты». Закоммичена в ветку `ai-lab` 2026-11-12 (патч `0004`), есть в `GeneralsXZH-AI.app` (пересобран 2026-11-12, тот же CRC, что в дуэли). Один матч с трейсом удобно запускать через `lab.match.run_match(..., keep=True)`, лог будет в `<папка>/<seed>-<id>/log.txt`.
- **Скорость** (M4 Pro): ~60x реального времени, 6 потоков - ~860 матчей в час.
- Всё установленное ради сборки (brew, vcpkg, Vulkan SDK) и команды удаления: `ai-lab/INSTALLED.md`.

## Идеи на потом

- Свой ИИ сильнее Improved AI: план и правила в скилле `.claude/skills/zh-ai-improve/SKILL.md`. Этап 1 (полигон) сделан 2026-11-07, см. раздел про ai-lab. Дальше этапы 2-3.
  Этап 2 начат 2026-11-07. База Improved AI против себя: `ai-lab/runs/baseline-derricks-2026-11-07/` (3 карты, все пары сторон, 270 матчей). GLA проигрывает США (27%), обыгрывает Китай (63%). Замена `CashBounty` на засаду и скрытую атаку у GLA ухудшила результат, откатана (`Mods/ImprovedAI_GLA/CHANGELOG.md`, вариант полигона `improved_ai_gla`). Жалобы пользователя: редкие однообразные атаки, слабая игра в бою, лёгкая защита от раша, бот не берёт нефтевышки. Сбор денег устраивает. Вышки и атаки живут в `.scb` (скрипты `Tech Building Detect/Near`, `Tech Stop Trying`), это этап 3.
  Этап 3 начат 2026-11-09: конвертер `tools/scb.py`, вариант `Mods/ImprovedAI_Plus/` (вариант полигона `improved_ai_plus`, ярлык `Запустить Zero Hour (Improved AI Plus).command`). Первая правка: отряд захвата больше не уходит в угол карты (0, 0), когда в зоне `CombatZone` нет техзданий, а охотится за ближайшим. Вышек на 5-й минуте стало в среднем 1.58 вместо 1.32 на игрока, на Tournament Desert вдвое больше. Подробности и цифры в `Mods/ImprovedAI_Plus/CHANGELOG.md`. Изменения движка (счётчики вышек, трейс) закоммичены в ветку `ai-lab` 2026-11-10. Первая дуэль Plus против Improved AI 1.2 в одних матчах (2026-11-10, 270 матчей): Plus выиграл 54%, критерий 60% не выполнен; на Tournament Lake Plus проигрывает (39%). Цифры в `Mods/ImprovedAI_Plus/CHANGELOG.md`.
  2026-11-10, вторая правка: отряд захвата снова заранее идёт к нефтевышке в `CombatZone` (тип `TechOilDerrick`, при пустой зоне движок приказа не даёт). Plus 55% против Improved AI, Lake 51%. Контроль Improved AI против себя в тех же матчах: 50% (`ai-lab/runs/control-improved-vs-improved-2026-11-10/`), сравнивать новые дуэли с ним попарно. Причина редких атак найдена трейсом: у атакующих команд минимум состава 0, команды уходят по 1-2 машины и откатываются к началу пути при каждом подкреплении. Две прямые правки (команда выходит только целиком из базы; только полным составом) дали 49% и 42%, отброшены. 2026-11-11 третья (минимум в половину полного состава) дала 46%, тоже отброшена: минимум состава атакующих команд больше не поднимать. Трейс юнитов включается, только если `AI_LAB_TRACE` - подстрока слова `Tech` (например `T` ловит команды с заглавной T в имени).
  2026-11-12, четвёртая правка: Plus 69% против Improved AI (186 из 270), критерий выполнен на всех картах и сторонах (слабая пара Китай против GLA, 50%). Состав: скрипты `* Time Escalation - H` раз в 7 с вместо 10 (волны атак раньше, это и дало прирост); у общих стартовых скриптов команд копии `<имя> OC` без `oneShot`, потому что движок выключает одноразовый скрипт для всего игрока и приказ получала только первая команда (раш GLA, США, Китая стоял на базе); охота раша GLA без кнопки диверсии. Отброшены: задержка запуска волн 20 с, по две копии атакующих команд, правка тыловой атаки Китая, эскалация раз в 5 с. Цифры в `Mods/ImprovedAI_Plus/CHANGELOG.md`.
  2026-11-12, пятая правка (жалоба: на Dust Devil бот не берёт вышку и нефтезавод в углу): порог `* Tech - Stop Trying` поднят со 100 до 143, 69% как и раньше, техзданий на Dust Devil вдвое больше. Правка движка (захват не выбирает вражеские здания, пока есть свободные) закоммичена в ветку `ai-lab` (патч `0005`), `GeneralsXZH-AI.app` пересобран: с ней 73% и втрое больше техзданий на Dust Devil. В обычном `GeneralsXZH.app` её нет, играть с ней через ярлык `(Improved AI Plus, свой движок)`.
  Всё, что ставится в систему ради ИИ, записано в `ai-lab/INSTALLED.md` с командами удаления. Снимок системы до начала: `ai-lab/baseline/`.

- Другие моды ИИ: Advanced AI mod, улучшенный AEI, v2.8 (https://www.moddb.com/mods/advanced-ai-mod-for-zero-hour-improved-by-aei). Он заменяет `SkirmishScripts.scb` и папку `INI`. Делать по той же схеме: папка в `Mods/` и отдельный ярлык.
- ShockWave на GeneralsX: в wiki есть страница How-to-Install-&-Play-Shockwave-Mod. Нужен .NET для `cicdec`.
- ModDB отвечает 403 на автоматические запросы. Файлы скачивает пользователь вручную.
