"""Дуэль ИИ: кандидат против соперника на нескольких картах за все пары сторон, вердикт по критерию.

Критерий (скилл zh-ai-improve): больше 60% побед минимум за 30 матчей, минимум на 3 картах,
кандидат играл за все 3 стороны, и ни один бот не стоял первые 2 минуты.

python3 -m lab.duel --candidate improved_ai_plus --opponent improved_ai --per-pair 10 --jobs 6 --out runs/<имя>/results.csv
python3 -m lab.duel --candidate improved_ai_plus --report runs/<имя>/results.csv
"""
import argparse
import csv
import signal
import sys
import time
from collections import defaultdict
from itertools import product
from pathlib import Path

from lab.match import MatchConfig, PlayerSpec
from lab.series import LAB, make_configs, run_series, summary

MAPS = ("maps\\alpine assault\\alpine assault.map",
        "maps\\tournament desert\\tournament desert.map",
        "maps\\tournament lake\\tournament lake.map")
FACTIONS = ("FactionAmerica", "FactionChina", "FactionGLA")
WIN_SHARE, MIN_MATCHES, MIN_MAPS = 0.60, 30, 3


def duel_configs(candidate: str, opponent: str, per_pair: int, maps=MAPS, factions=FACTIONS,
                 difficulty: str = "hard", max_minutes: int = 90) -> list[MatchConfig]:
    # данные (INI) общие от соперника, кандидату подменяется только .scb
    cfgs = []
    for m, cf, of in product(maps, factions, factions):
        players = (PlayerSpec(cf, difficulty, candidate), PlayerSpec(of, difficulty))
        cfgs += make_configs(m, players, opponent, per_pair, max_minutes=max_minutes)
    return cfgs


def _short(m: str) -> str:
    return m.split("\\")[-1].removesuffix(".map")


def verdict(csv_path: Path, candidate: str) -> str:
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    games = []   # (карта, сторона кандидата, сторона соперника, победил ли кандидат)
    idle, broken = [], []
    for r in rows:
        scripts, factions = r["scripts"].split("|"), r["factions"].split("|")
        if candidate not in scripts:
            continue
        slot = scripts.index(candidate)
        if r["status"] in ("hung", "crash"):
            broken.append(r["seed"])
            continue
        start = [int(x) for x in r["structures_at_start"].split("|")]
        at2 = [int(x) if x else None for x in r["structures_at_2min"].split("|")]
        if any(a is not None and a <= s for s, a in zip(start, at2)):
            idle.append(f'{_short(r["map"])} seed {r["seed"]}')
        won = r["winner_slot"] != "" and int(r["winner_slot"]) == slot
        games.append((r["map"], factions[slot], factions[1 - slot], won))

    def rate(sel) -> str:
        n = len(sel)
        w = sum(1 for g in sel if g[3])
        return f"{w}/{n} ({w / n:.0%})" if n else "0/0"

    total = sum(1 for g in games if g[3]) / len(games) if games else 0.0
    maps = sorted({g[0] for g in games})
    sides = sorted({g[1] for g in games})
    lines = [f"кандидат {candidate}: побед {rate(games)}"]
    lines += [f"  {_short(m)}: {rate([g for g in games if g[0] == m])}" for m in maps]
    lines += [f"  за {s}: {rate([g for g in games if g[1] == s])}" for s in sides]
    by_pair = defaultdict(list)
    for g in games:
        by_pair[(g[1], g[2])].append(g)
    lines.append("  пары (кандидат против соперника): " + ", ".join(
        f"{c.removeprefix('Faction')}-{o.removeprefix('Faction')} {rate(v)}" for (c, o), v in sorted(by_pair.items())))
    lines.append(f"  вылеты и зависания: {len(broken)}; бот не строился первые 2 минуты: {len(idle)}"
                 + (f" ({', '.join(idle[:5])})" if idle else ""))
    checks = {
        f"побед больше {WIN_SHARE:.0%}": total > WIN_SHARE,
        f"матчей не меньше {MIN_MATCHES}": len(games) >= MIN_MATCHES,
        f"карт не меньше {MIN_MAPS}": len(maps) >= MIN_MAPS,
        "все 3 стороны": len(sides) >= 3,
        "все боты строились": not idle,
    }
    lines.append("  критерий: " + ", ".join(f"{k} {'да' if v else 'НЕТ'}" for k, v in checks.items()))
    lines.append(f"  итог: {'ЛУЧШЕ' if all(checks.values()) else 'не лучше'}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Дуэль ИИ: кандидат против соперника, вердикт по критерию")
    ap.add_argument("--candidate", required=True, help="вариант, чей .scb у кандидата")
    ap.add_argument("--opponent", help="вариант соперника, его данные общие для обоих")
    ap.add_argument("--per-pair", type=int, default=10, help="матчей на карту и пару сторон")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--report", type=Path, help="только вердикт по готовому CSV")
    ap.add_argument("--root", type=Path, default=LAB.parent)
    ap.add_argument("--app", type=Path, default=LAB / "GeneralsXZH-AI.app")
    a = ap.parse_args(argv)
    if a.report:
        print(verdict(a.report, a.candidate))
        return 0
    if not (a.opponent and a.out):
        ap.error("нужны --opponent и --out (или --report)")
    cfgs = duel_configs(a.candidate, a.opponent, a.per_pair)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    start = time.monotonic()
    try:
        results = run_series(cfgs, root=a.root.resolve(), app=a.app.resolve(), out_csv=a.out.resolve(), jobs=a.jobs)
    except KeyboardInterrupt:
        print("прервано", file=sys.stderr)
        return 130
    print(summary(results, time.monotonic() - start))
    print(verdict(a.out, a.candidate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
