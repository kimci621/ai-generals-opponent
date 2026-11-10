import threading
import unittest

from helpers import MOD_SCB, VANILLA_SCB, make_fake_root, snapshot
from lab.variants import ensure_variant, player_scripts


class VariantsTest(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_fake_root()

    def tearDown(self):
        self.tmp.cleanup()

    def test_vanilla_restores_original_scripts(self):
        d = ensure_variant("vanilla", self.root)
        self.assertEqual(d, self.root / "ai-lab/data/vanilla")
        self.assertEqual((d / "Data/Scripts/SkirmishScripts.scb").read_bytes(), VANILLA_SCB)
        self.assertFalse((d / "Data/INI").exists())

    def test_improved_ai_overlays_mod(self):
        d = ensure_variant("improved_ai", self.root)
        self.assertEqual((d / "Data/Scripts/SkirmishScripts.scb").read_bytes(), MOD_SCB)
        self.assertEqual((d / "Data/INI/Default/AIData.ini").read_text(), "mod")
        self.assertTrue((d / "INIZH.big").exists())
        self.assertFalse((d / "Data/INI/x.ini").exists())

    def test_source_untouched(self):
        before = snapshot(self.root / "GeneralsZH")
        ensure_variant("vanilla", self.root)
        ensure_variant("improved_ai", self.root)
        self.assertEqual(snapshot(self.root / "GeneralsZH"), before)

    def test_player_scripts_only_scb_may_differ(self):
        plus = self.root / "Mods/ImprovedAI_Plus/Data"
        (plus / "Scripts").mkdir(parents=True)
        (plus / "INI/Default").mkdir(parents=True)
        (plus / "Scripts/SkirmishScripts.scb").write_bytes(b"plus-scb")
        (plus / "INI/Default/AIData.ini").write_text("mod")
        p = player_scripts("improved_ai_plus", "improved_ai", self.root)
        self.assertEqual(p, self.root / "ai-lab/data/improved_ai_plus/Data/Scripts/SkirmishScripts.scb")
        self.assertEqual(p.read_bytes(), b"plus-scb")
        # у ванили нет INI мода: свой .scb поверх общих INI дал бы нечестный матч
        with self.assertRaises(ValueError):
            player_scripts("vanilla", "improved_ai", self.root)
        (plus / "INI/Default/AIData.ini").write_text("other")
        with self.assertRaises(ValueError):
            player_scripts("improved_ai_plus", "improved_ai", self.root)

    def test_incomplete_variant_rebuilt(self):
        broken = self.root / "ai-lab/data/vanilla"
        broken.mkdir(parents=True)
        (broken / "junk").write_text("x")
        d = ensure_variant("vanilla", self.root)
        self.assertFalse((d / "junk").exists())
        self.assertTrue((d / ".variant-ok").exists())
        self.assertTrue((d / "INIZH.big").exists())

    def test_concurrent_calls(self):
        out, errors = [], []

        def call():
            try:
                out.append(ensure_variant("improved_ai", self.root))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=call) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(set(out)), 1)
        d = out[0]
        self.assertFalse((d / "GeneralsZH").exists())
        self.assertTrue((d / ".variant-ok").exists())
        self.assertEqual(list((self.root / "ai-lab/data").glob(".improved_ai.tmp-*")), [])

    def test_unknown_variant_raises(self):
        with self.assertRaises(ValueError):
            ensure_variant("nope", self.root)


if __name__ == "__main__":
    unittest.main()
