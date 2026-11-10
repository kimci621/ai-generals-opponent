"""Варианты данных Zero Hour: APFS-клон GeneralsZH, приведённый к ванили, плюс оверлей мода."""
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

VARIANTS: dict[str, Path | None] = {
    "vanilla": None,
    "improved_ai": Path("Mods/ImprovedAI_1.2/Data"),
    "improved_ai_gla": Path("Mods/ImprovedAI_GLA/Data"),
    "improved_ai_plus": Path("Mods/ImprovedAI_Plus/Data"),
}

_lock = threading.Lock()
SCB = Path("Scripts/SkirmishScripts.scb")


def ensure_variant(name: str, root: Path) -> Path:
    if name not in VARIANTS:
        raise ValueError(f"неизвестный вариант: {name}")
    data = root / "ai-lab/data"
    dst = data / name
    # ponytail: блокировка только между потоками одного процесса; серии в разных процессах параллельно не собирают варианты
    with _lock:
        if (dst / ".variant-ok").exists():
            return dst
        data.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        tmp = data / f".{name}.tmp-{uuid.uuid4().hex}"
        try:
            # tmp ещё не существует, иначе cp положит копию внутрь
            subprocess.run(["cp", "-cR", str(root / "GeneralsZH"), str(tmp)], check=True)
            # к ванили, даже если GeneralsZH «грязный» после ярлыка с модом
            shutil.copyfile(root / "Mods/vanilla_backup/SkirmishScripts.scb", tmp / "Data/Scripts/SkirmishScripts.scb")
            shutil.rmtree(tmp / "Data/INI", ignore_errors=True)
            overlay = VARIANTS[name]
            if overlay is not None:
                shutil.copytree(root / overlay, tmp / "Data", dirs_exist_ok=True)
            (tmp / ".variant-ok").touch()
            tmp.rename(dst)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return dst


def player_scripts(name: str, base: str, root: Path) -> Path:
    """SkirmishScripts.scb варианта name для одного игрока в матче на данных варианта base.

    Движок подменяет игроку только .scb, INI у всех общие (из base). Поэтому варианты
    должны отличаться только этим файлом, иначе сравнение нечестное."""
    def overlay(v: str) -> dict[str, bytes]:
        if v not in VARIANTS:
            raise ValueError(f"неизвестный вариант: {v}")
        src = VARIANTS[v]
        if src is None:
            return {}
        d = root / src
        return {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*")
                if p.is_file() and p.name != ".DS_Store" and p.relative_to(d) != SCB}
    if overlay(name) != overlay(base):
        raise ValueError(f"варианты {name} и {base} отличаются не только {SCB}, свой .scb на игрока не подойдёт")
    return ensure_variant(name, root) / "Data" / SCB
