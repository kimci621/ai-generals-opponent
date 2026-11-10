import os
import subprocess
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from helpers import make_fake_root
from lab import match
from lab.match import MatchConfig, PlayerSpec, default_wall_timeout, engine_args, kill_all, run_match

FAKE_APP = Path(__file__).parent / "fake_app"
MAP = "maps\\alpine assault\\alpine assault.map"
PLAYERS = (PlayerSpec("FactionGLA", "hard"), PlayerSpec("FactionAmerica", "hard"))


def cfg(**kw) -> MatchConfig:
    return MatchConfig(**{"map": MAP, "players": PLAYERS, "seed": 7, "variant": "vanilla", **kw})


def alive(marker: str) -> bool:
    return subprocess.run(["pgrep", "-f", marker], capture_output=True).returncode == 0


class MatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_fake_root()
        self.runs = self.root / "runs"
        self.marker = f"fake-hang-{uuid.uuid4().hex}"

    def tearDown(self):
        match._stopping.clear()
        self.tmp.cleanup()

    def run_fake(self, mode: str, **kw):
        with mock.patch.dict(os.environ, {"FAKE_MODE": mode, "FAKE_MARKER": self.marker}):
            return run_match(cfg(), root=self.root, app=FAKE_APP, runs_dir=self.runs, **kw)

    def test_engine_args(self):
        args = engine_args(cfg(), Path("/r/result.json"))
        self.assertEqual(args[:2], ["-headless", "-aiMatch"])
        i = args.index("-aiPlayer")
        self.assertEqual(args[i:i + 4], ["-aiPlayer", "FactionGLA:hard", "-aiPlayer", "FactionAmerica:hard"])
        self.assertEqual(args[args.index("-aiSeed") + 1], "7")
        self.assertEqual(args[args.index("-aiMap") + 1], MAP)
        self.assertEqual(args[args.index("-aiResult") + 1], "/r/result.json")
        self.assertNotIn("-seed", args)

    def test_engine_args_own_scripts(self):
        c = cfg(variant="improved_ai", players=(PlayerSpec("FactionGLA", "hard", "improved_ai"), PLAYERS[1]))
        args = engine_args(c, Path("/r/result.json"), self.root)
        scb = self.root / "ai-lab/data/improved_ai/Data/Scripts/SkirmishScripts.scb"
        i = args.index("-aiPlayer")
        self.assertEqual(args[i:i + 4], ["-aiPlayer", f"FactionGLA:hard:{scb}", "-aiPlayer", "FactionAmerica:hard"])

    def test_win_parsed(self):
        r = self.run_fake("win")
        self.assertEqual(r.status, "win")
        self.assertEqual(r.winner_slot, 0)
        self.assertEqual(r.structures_at_start, (1, 1))
        self.assertEqual(r.structures_at_2min, (5, 6))
        self.assertEqual((r.derricks_on_map, r.tech_on_map), (4, 6))
        self.assertEqual(r.derricks, ((1, 2, 3), (0, 1, None)))
        self.assertEqual(r.tech, ((1, 2, 4), (0, 1, 1)))
        self.assertIsInstance(r.final_crc, int)
        self.assertIsNone(r.run_dir)

    def test_draw_parsed(self):
        r = self.run_fake("draw")
        self.assertEqual(r.status, "draw")
        self.assertIsNone(r.winner_slot)

    def test_crash_keeps_run_dir(self):
        r = self.run_fake("crash")
        self.assertEqual(r.status, "crash")
        self.assertTrue((r.run_dir / "log.txt").exists())

    def test_hang_kills_process_group(self):
        r = self.run_fake("hang", wall_timeout_s=2)
        self.assertEqual(r.status, "hung")
        self.assertFalse(alive(self.marker))

    def test_kill_all_aborts(self):
        out = []
        t = threading.Thread(target=lambda: out.append(self.run_fake("hang")))
        t.start()
        time.sleep(1)
        kill_all()
        t.join(3)
        self.assertFalse(t.is_alive())
        self.assertEqual(out[0].status, "aborted")
        self.assertFalse(alive(self.marker))

    def test_home_is_sandboxed(self):
        r = self.run_fake("win", keep=True)
        self.assertTrue((r.run_dir / "home/Library/Application Support/GeneralsX/touched").exists())

    def test_default_wall_timeout(self):
        self.assertEqual(default_wall_timeout(cfg(max_minutes=10)), 900)
        self.assertEqual(default_wall_timeout(cfg(max_minutes=90)), 5400)


if __name__ == "__main__":
    unittest.main()
