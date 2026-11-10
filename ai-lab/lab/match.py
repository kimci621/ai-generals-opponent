"""Один матч ИИ против ИИ: песочница HOME, запуск движка в режиме -aiMatch, разбор result.json."""
import json
import os
import shutil
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from lab.variants import ensure_variant


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
    structures_at_start: tuple[int | None, ...]
    structures_at_2min: tuple[int | None, ...]
    final_crc: int | None
    run_dir: Path | None
    # нефтевышки и все техздания: на карте при старте; у каждого игрока [5 мин, 10 мин, конец]
    derricks_on_map: int | None = None
    derricks: tuple[tuple[int | None, ...], ...] = ()
    tech_on_map: int | None = None
    tech: tuple[tuple[int | None, ...], ...] = ()


# живые движки: Popen -> убит ли через kill_all
_procs: dict[subprocess.Popen, bool] = {}
_lock = threading.Lock()
_stopping = threading.Event()


def engine_args(cfg: MatchConfig, result_path: Path) -> list[str]:
    args = ["-headless", "-aiMatch", "-aiMap", cfg.map]
    for p in cfg.players:
        args += ["-aiPlayer", f"{p.faction}:{p.difficulty}"]
    return args + ["-aiSeed", str(cfg.seed), "-aiCash", str(cfg.cash),
                   "-aiMaxMinutes", str(cfg.max_minutes), "-aiResult", str(result_path)]


def default_wall_timeout(cfg: MatchConfig) -> float:
    return max(900, cfg.max_minutes * 60)


def kill_all() -> None:
    with _lock:
        _stopping.set()
        for p in _procs:
            _procs[p] = True
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def run_match(cfg: MatchConfig, *, root: Path, app: Path, runs_dir: Path,
              wall_timeout_s: float | None = None, keep: bool = False) -> MatchResult:
    n = len(cfg.players)
    empty = (None,) * n
    run = runs_dir / f"{cfg.seed}-{uuid.uuid4().hex[:8]}"
    (run / "home").mkdir(parents=True)
    result_path = run / "result.json"
    env = {**os.environ,
           "HOME": str(run / "home"),
           "CNC_GENERALS_PATH": str(root / "Generals"),
           "CNC_GENERALS_ZH_PATH": str(ensure_variant(cfg.variant, root))}
    start = time.monotonic()
    with _lock:
        if _stopping.is_set():
            return MatchResult(cfg, "aborted", None, None, 0.0, empty, empty, None, run)
        with open(run / "log.txt", "wb") as log:
            proc = subprocess.Popen([str(app / "Contents/MacOS/run.sh"), *engine_args(cfg, result_path)],
                                    env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        _procs[proc] = False
    status = None
    try:
        proc.wait(timeout=wall_timeout_s or default_wall_timeout(cfg))
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        status = "hung"
    with _lock:
        if _procs.pop(proc):
            status = "aborted"
    wall = time.monotonic() - start

    data = None
    if status is None:
        if proc.returncode == 0 and result_path.exists():
            data = json.loads(result_path.read_text())
            status = data["outcome"]
        else:
            status = "crash"
    if data is None:
        return MatchResult(cfg, status, None, None, wall, empty, empty, None, run)

    players = sorted(data["players"], key=lambda p: p["slot"])
    winners = [p["slot"] for p in players if p["won"]]
    if status in ("win", "draw", "timeout") and not keep:
        shutil.rmtree(run, ignore_errors=True)
        run = None
    return MatchResult(cfg, status, winners[0] if len(winners) == 1 else None, data["game_seconds"], wall,
                       tuple(p["structures_at_start"] for p in players),
                       tuple(p["structures_at_2min"] for p in players),
                       data["final_crc"], run,
                       data.get("derricks_on_map"), tuple(tuple(p.get("derricks", ())) for p in players),
                       data.get("tech_on_map"), tuple(tuple(p.get("tech_buildings", ())) for p in players))
