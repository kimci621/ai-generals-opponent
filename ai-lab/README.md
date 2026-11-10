# ai-lab

Полигон для своего ИИ Zero Hour: своя сборка движка GeneralsX и матчи ИИ против ИИ.

- `engine/GeneralsX` - исходники движка, ветка `ai-lab`; `GeneralsXZH-AI.app` - своя сборка (`scripts/build-ai-app.sh`), запуск `scripts/run-ai.sh`.
- `lab/` - полигон на Python (только стандартная библиотека): `variants.py` готовит данные под вариант ИИ, `match.py` гоняет один матч, `series.py` - серию с CSV. Тесты: `python3 -m unittest discover -s lab/tests -v`.
- Серия на ночь: `caffeinate -is python3 -m lab.series --variant improved_ai --map "maps\alpine assault\alpine assault.map" --player FactionGLA:hard --player FactionAmerica:hard --matches 30 --jobs 6 --out runs/<имя>/results.csv`.
- Замеры 2026-11-07 (M4 Pro, 8+4 ядра, Alpine Assault, Improved AI Hard GLA против США): матч идёт в ~60 раз быстрее реального времени, в среднем 20-30 мин игры за 20-30 с. 4 потока - 630 матчей в час, 6 - 860, 8 - 1090; один матч на 8 потоках медленнее всего на 9%, CRC при 4 и 8 потоках одинаковые. Приёмка: 30 матчей, 0 `hung`/`crash`, все боты строились в первые 2 минуты, США выиграли 21 из 30.
- Дуэль «кандидат против соперника» в одних матчах (свой `SkirmishScripts.scb` на игрока, `-aiPlayer Faction:hard:<scb>`): `caffeinate -is python3 -m lab.duel --candidate improved_ai_plus --opponent improved_ai --per-pair 10 --jobs 6 --out runs/<имя>/results.csv`. Печатает вердикт по критерию скилла `zh-ai-improve`; по готовому CSV: `python3 -m lab.duel --candidate improved_ai_plus --report runs/<имя>/results.csv`.
- `docs/` - замысел и планы, `INSTALLED.md` - что поставлено в систему и как удалить, `baseline/` - снимок системы до начала.
