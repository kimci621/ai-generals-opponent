"""Серия матчей ИИ против ИИ: параллельный запуск, CSV по мере готовности, сводка.

python3 -m lab.series --variant improved_ai --map "maps\\alpine assault\\alpine assault.map" \
    --player FactionGLA:hard --player FactionAmerica:hard --matches 30 --jobs 6 --out runs/<имя>/results.csv
"""
import argparse
import csv
import signal
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from lab.match import MatchConfig, MatchResult, PlayerSpec, kill_all, run_match
from lab.variants import ensure_variant

LAB = Path(__file__).resolve().parents[1]

CSV_COLUMNS = ["seed", "variant", "map", "factions", "difficulties", "status",
               "winner_slot", "winner_faction", "game_seconds", "wall_seconds",
               "structures_at_start", "structures_at_2min", "final_crc", "run_dir",
               "derricks_on_map", "derricks_5min", "derricks_10min", "derricks_end", "tech_on_map", "tech_end"]


def make_configs(map: str, players: tuple[PlayerSpec, ...], variant: str,
                 matches: int, first_seed: int = 1, swap_slots: bool = True,
                 max_minutes: int = 90) -> list[MatchConfig]:
    # в нечётных матчах (2-м, 4-м...) игроки меняются слотами, чтобы слот не давал перекоса
    return [MatchConfig(map, players[::-1] if swap_slots and i % 2 else players, first_seed + i, variant,
                        max_minutes=max_minutes)
            for i in range(matches)]


def _join(values) -> str:
    return "|".join("" if v is None else str(v) for v in values)


def _row(r: MatchResult) -> list:
    c = r.config
    winner = c.players[r.winner_slot].faction if r.winner_slot is not None else ""
    return [c.seed, c.variant, c.map, _join(p.faction for p in c.players), _join(p.difficulty for p in c.players),
            r.status, "" if r.winner_slot is None else r.winner_slot, winner,
            "" if r.game_seconds is None else r.game_seconds, round(r.wall_seconds, 1),
            _join(r.structures_at_start), _join(r.structures_at_2min),
            "" if r.final_crc is None else r.final_crc, r.run_dir or "",
            "" if r.derricks_on_map is None else r.derricks_on_map,
            *(_join(p[k] if len(p) > k else None for p in r.derricks) for k in range(3)),
            "" if r.tech_on_map is None else r.tech_on_map, _join(p[2] if len(p) > 2 else None for p in r.tech)]


def run_series(cfgs: list[MatchConfig], *, root: Path, app: Path, out_csv: Path,
               jobs: int, wall_timeout_s: float | None = None) -> list[MatchResult]:
    for v in sorted({c.variant for c in cfgs}):
        ensure_variant(v, root)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    results = []
    ex = ThreadPoolExecutor(max_workers=jobs)
    try:
        with open(out_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(CSV_COLUMNS)
            f.flush()
            futures = [ex.submit(run_match, c, root=root, app=app, runs_dir=out_csv.parent,
                                 wall_timeout_s=wall_timeout_s) for c in cfgs]
            for fut in as_completed(futures):
                r = fut.result()
                if r.status == "aborted":
                    continue
                results.append(r)
                w.writerow(_row(r))
                f.flush()
    except KeyboardInterrupt:
        kill_all()
        ex.shutdown(wait=True, cancel_futures=True)
        raise
    ex.shutdown()
    return results


def summary(results: list[MatchResult], wall: float) -> str:
    n = len(results)
    if not n:
        return "матчей: 0"
    wins = Counter(r.config.players[r.winner_slot].faction for r in results if r.winner_slot is not None)
    statuses = Counter(r.status for r in results)
    games = [r.game_seconds for r in results if r.game_seconds is not None]
    lines = [f"матчей: {n}"]
    lines += [f"  победы {f}: {k} ({k / n:.0%})" for f, k in wins.most_common()]
    lines.append("  " + ", ".join(f"{s}: {statuses[s]}" for s in ("draw", "timeout", "hung", "crash")))
    if games:
        lines.append(f"  среднее время матча: {sum(games) / len(games) / 60:.1f} мин игры")
    lines.append(f"  матчей в час: {n / wall * 3600:.0f}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Серия матчей ИИ против ИИ")
    ap.add_argument("--variant", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--player", action="append", required=True, help="Faction:difficulty, по одному на слот")
    ap.add_argument("--matches", type=int, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--first-seed", type=int, default=1)
    ap.add_argument("--max-minutes", type=int, default=90)
    ap.add_argument("--no-swap", action="store_true")
    ap.add_argument("--root", type=Path, default=LAB.parent)
    ap.add_argument("--app", type=Path, default=LAB / "GeneralsXZH-AI.app")
    a = ap.parse_args(argv)
    players = tuple(PlayerSpec(*p.split(":", 1)) for p in a.player)
    cfgs = make_configs(a.map, players, a.variant, a.matches, a.first_seed, not a.no_swap, a.max_minutes)
    # фоновый запуск из shell наследует игнор SIGINT; Ctrl+C должен работать всегда
    signal.signal(signal.SIGINT, signal.default_int_handler)
    start = time.monotonic()
    try:
        results = run_series(cfgs, root=a.root.resolve(), app=a.app.resolve(), out_csv=a.out.resolve(), jobs=a.jobs)
    except KeyboardInterrupt:
        print("прервано", file=sys.stderr)
        return 130
    print(summary(results, time.monotonic() - start))
    return 0


if __name__ == "__main__":
    sys.exit(main())
