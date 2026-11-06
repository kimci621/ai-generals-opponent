"""Фальшивый корень установки для тестов: маленькие файлы вместо .big."""
import tempfile
from pathlib import Path

VANILLA_SCB = b"vanilla-scb"
MOD_SCB = b"mod-scb"


def make_fake_root() -> tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    zh = root / "GeneralsZH"
    (zh / "Data/Scripts").mkdir(parents=True)
    (zh / "Data/INI").mkdir(parents=True)
    (zh / "INIZH.big").write_bytes(b"big")
    # «грязный» GeneralsZH, как после аварийного выхода из ярлыка с модом
    (zh / "Data/Scripts/SkirmishScripts.scb").write_bytes(MOD_SCB)
    (zh / "Data/INI/x.ini").write_text("x")
    (root / "Generals").mkdir()
    (root / "Mods/vanilla_backup").mkdir(parents=True)
    (root / "Mods/vanilla_backup/SkirmishScripts.scb").write_bytes(VANILLA_SCB)
    mod = root / "Mods/ImprovedAI_1.2/Data"
    (mod / "Scripts").mkdir(parents=True)
    (mod / "INI/Default").mkdir(parents=True)
    (mod / "Scripts/SkirmishScripts.scb").write_bytes(MOD_SCB)
    (mod / "INI/Default/AIData.ini").write_text("mod")
    return tmp, root


def snapshot(path: Path) -> dict[str, bytes]:
    return {str(p.relative_to(path)): p.read_bytes() for p in sorted(path.rglob("*")) if p.is_file()}
