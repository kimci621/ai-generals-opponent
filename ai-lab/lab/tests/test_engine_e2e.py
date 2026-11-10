"""E2E с настоящим движком. Пропускается без ai-lab/GeneralsXZH-AI.app. Таймаут: AI_E2E_TIMEOUT."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lab.match import MatchConfig, PlayerSpec, default_wall_timeout, engine_args, run_match

LAB = Path(__file__).resolve().parents[2]
ROOT = LAB.parent
APP = LAB / "GeneralsXZH-AI.app"
MAP = "maps\\alpine assault\\alpine assault.map"
PLAYERS = (PlayerSpec("FactionGLA", "hard"), PlayerSpec("FactionAmerica", "hard"))


def run(**kw):
    keep = kw.pop("keep", False)
    cfg = MatchConfig(**{"map": MAP, "players": PLAYERS, "seed": 1, "variant": "vanilla", **kw})
    timeout = float(os.environ.get("AI_E2E_TIMEOUT", default_wall_timeout(cfg)))
    return run_match(cfg, root=ROOT, app=APP, runs_dir=E2ETest.runs, wall_timeout_s=timeout, keep=keep)


@unittest.skipUnless(APP.exists(), "нет GeneralsXZH-AI.app")
class E2ETest(unittest.TestCase):
    runs: Path

    @classmethod
    def setUpClass(cls):
        cls.runs = Path(tempfile.mkdtemp(prefix="ai-e2e-"))
        cls.full = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.runs, ignore_errors=True)

    def full_match(self):
        if E2ETest.full is None:
            E2ETest.full = run(seed=1, keep=True)
        return E2ETest.full

    def test_match_finishes(self):
        r = self.full_match()
        self.assertIn(r.status, ("win", "draw", "timeout"), r.run_dir)
        data = json.loads((r.run_dir / "result.json").read_text())
        if r.status == "win":
            self.assertEqual(sum(p["won"] for p in data["players"]), 1)
        self.assertGreater(r.game_seconds, 0)
        self.assertEqual(data["seed"], 1)

    def test_ai_builds_in_first_2min(self):
        r = self.full_match()
        for start, at2 in zip(r.structures_at_start, r.structures_at_2min):
            self.assertGreater(at2, start)

    def test_timeout(self):
        r = run(max_minutes=1)
        self.assertEqual(r.status, "timeout")
        self.assertTrue(59 <= r.game_seconds <= 61, r.game_seconds)
        self.assertEqual(r.structures_at_2min, (None, None))

    def test_bad_faction_exit_3(self):
        r = run(players=(PlayerSpec("FactionNope", "hard"), PLAYERS[1]))
        self.assertEqual(r.status, "crash")
        self.assertIn("[AIMatch] error: unknown faction 'FactionNope'", (r.run_dir / "log.txt").read_text())

    def test_deterministic(self):
        a = run(seed=5, max_minutes=10, keep=True)
        b = run(seed=5, max_minutes=10, keep=True)
        sa = json.loads((a.run_dir / "result.json").read_text())["seed"]
        sb = json.loads((b.run_dir / "result.json").read_text())["seed"]
        self.assertEqual((sa, sb), (5, 5))
        for field in ("final_crc", "game_seconds", "winner_slot", "structures_at_2min"):
            self.assertEqual(getattr(a, field), getattr(b, field), field)

    def test_own_scripts_same_file_same_game(self):
        # свой .scb, побайтно равный общему, не меняет игру: подмена и возврат шаблонов честные
        base = run(seed=3, max_minutes=10, variant="improved_ai")
        own = run(seed=3, max_minutes=10, variant="improved_ai", keep=True,
                  players=(PLAYERS[0], PlayerSpec("FactionAmerica", "hard", "improved_ai")))
        self.assertIn("player1 uses skirmish scripts", (own.run_dir / "log.txt").read_text())
        self.assertEqual(own.final_crc, base.final_crc)

    def test_own_scripts_missing_file_exit_3(self):
        cfg = MatchConfig(MAP, (PLAYERS[0], PLAYERS[1]), 1, "vanilla")
        args = engine_args(cfg, E2ETest.runs / "x.json")
        args[args.index("FactionAmerica:hard")] = "FactionAmerica:hard:/nonexistent.scb"
        env = {**os.environ, "HOME": str(E2ETest.runs), "CNC_GENERALS_PATH": str(ROOT / "Generals"),
               "CNC_GENERALS_ZH_PATH": str(ROOT / "ai-lab/data/vanilla")}
        p = subprocess.run([str(APP / "Contents/MacOS/run.sh"), *args], env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 3)
        self.assertIn("cannot open skirmish scripts '/nonexistent.scb'", p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
