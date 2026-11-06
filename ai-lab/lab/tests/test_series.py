import csv
import os
import signal
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from helpers import make_fake_root
from lab import match
from lab.match import PlayerSpec
from lab.series import CSV_COLUMNS, make_configs, run_series

LAB = Path(__file__).resolve().parents[2]
FAKE_APP = Path(__file__).parent / "fake_app"
MAP = "maps\\alpine assault\\alpine assault.map"
PLAYERS = (PlayerSpec("FactionGLA", "hard"), PlayerSpec("FactionAmerica", "hard"))


def rows(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class SeriesTest(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_fake_root()
        self.out = self.root / "runs/s/results.csv"
        self.marker = f"fake-hang-{uuid.uuid4().hex}"

    def tearDown(self):
        match._stopping.clear()
        self.tmp.cleanup()

    def series(self, mode: str, n: int):
        with mock.patch.dict(os.environ, {"FAKE_MODE": mode}):
            return run_series(make_configs(MAP, PLAYERS, "vanilla", n), root=self.root, app=FAKE_APP,
                              out_csv=self.out, jobs=2)

    def test_make_configs_swaps_slots(self):
        cfgs = make_configs(MAP, PLAYERS, "vanilla", 4)
        self.assertEqual([c.seed for c in cfgs], [1, 2, 3, 4])
        self.assertEqual(cfgs[0].players, PLAYERS)
        self.assertEqual(cfgs[1].players, PLAYERS[::-1])
        self.assertEqual(cfgs[2].players, PLAYERS)
        self.assertEqual(cfgs[3].players, PLAYERS[::-1])

    def test_csv_written_incrementally(self):
        self.series("win", 3)
        with open(self.out, newline="") as f:
            self.assertEqual(next(csv.reader(f)), CSV_COLUMNS)
        got = {int(r["seed"]): r for r in rows(self.out)}
        self.assertEqual(sorted(got), [1, 2, 3])
        # фейк всегда отдаёт победу слоту 0; во 2-м матче в слоте 0 США
        self.assertEqual(got[1]["winner_faction"], "FactionGLA")
        self.assertEqual(got[2]["winner_faction"], "FactionAmerica")
        self.assertEqual(got[2]["factions"], "FactionAmerica|FactionGLA")

    def test_failed_matches_recorded(self):
        self.series("crash", 2)
        for r in rows(self.out):
            self.assertEqual(r["status"], "crash")
            self.assertNotEqual(r["run_dir"], "")

    def test_interrupt_kills_all(self):
        env = {**os.environ, "FAKE_MODE": "hang", "FAKE_MARKER": self.marker}
        p = subprocess.Popen([sys.executable, "-m", "lab.series", "--variant", "vanilla", "--map", MAP,
                              "--player", "FactionGLA:hard", "--player", "FactionAmerica:hard",
                              "--matches", "4", "--jobs", "2", "--out", str(self.out),
                              "--root", str(self.root), "--app", str(FAKE_APP)],
                             cwd=LAB, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        p.send_signal(signal.SIGINT)
        self.assertEqual(p.wait(5), 130)
        self.assertNotEqual(subprocess.run(["pgrep", "-f", self.marker], capture_output=True).returncode, 0)
        self.assertEqual(rows(self.out), [])


if __name__ == "__main__":
    unittest.main()
