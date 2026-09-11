"""Temiz Windows ortamında paket açılış kontrolü — `F6-005`.

Kabul: **Sistem Python kurulumu olmadan ana ekran açılır.**

Paketin "kendi kendine yettiği", geliştirme makinesinde çalıştırılarak
bilinemez: o makinede Python zaten kuruludur ve paket farkında olmadan
ondan yararlanıyor olabilir (`PYTHONPATH`, `PYTHONHOME`, `PATH`
üzerindeki yorumlayıcı). Bu araç ortamı **temizleyerek** çalıştırır:

* `PYTHON*` değişkenleri (``PYTHONPATH``, ``PYTHONHOME`` vb.) silinir,
* `PATH`'ten Python ve venv dizinleri çıkarılır,
* paket bu ortamda açılır ve `--self-check` ile ana ekranın gerçekten
  açıldığı doğrulanır.

Bu, **gerçek bir temiz Windows kurulumu değildir** ve rapor bunu
gizlemez: aynı makinede sistem kütüphaneleri (Visual C++ runtime gibi)
hâlâ mevcuttur. Ölçülen şey, paketin Python'a bağımlı olup olmadığıdır.

Kullanım::

    .venv\\Scripts\\python.exe tools\\clean_env_check.py
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIST = ROOT / "dist"
DEFAULT_REPORT = ROOT / "docs" / "packaging" / "results" / "clean-env-check.json"

#: PATH'ten cikarilacak dizin isaretleri (kucuk harfe cevrilerek aranir).
PYTHON_PATH_MARKERS: tuple[str, ...] = (
    "python",
    ".venv",
    "venv",
    "conda",
    "msys64",
    "mingw",
    # Microsoft Store "app execution alias" dizini: icinde python.exe ve
    # python3.exe saplamalari bulunur ve PATH'te birakilirsa ortam
    # "Python'suz" sayilamaz.
    "windowsapps",
)


@dataclass
class CleanEnvResult:
    """Temiz ortam koşusunun sonucu."""

    executable: str
    version_reported: str = ""
    self_check_exit: int = -1
    self_check_lines: list[str] = field(default_factory=lambda: [])
    removed_env_vars: list[str] = field(default_factory=lambda: [])
    removed_path_entries: int = 0
    remaining_path_entries: int = 0
    python_on_path: bool = True
    machine: dict[str, str] = field(default_factory=lambda: {})

    @property
    def ok(self) -> bool:
        """Ana ekran açıldıysa ve Python ortamdan çıkarıldıysa geçer."""
        return self.self_check_exit == 0 and not self.python_on_path


def scrub_environment(
    source: dict[str, str] | None = None,
) -> tuple[dict[str, str], list[str], int]:
    """Python izlerini temizlenmiş bir ortam üretir.

    Döner: (ortam, silinen değişkenler, PATH'ten çıkarılan girdi sayısı).
    """
    base = dict(os.environ if source is None else source)

    removed_vars = sorted(name for name in base if name.upper().startswith("PYTHON"))
    for name in removed_vars:
        base.pop(name, None)

    path_value = base.get("PATH", "")
    entries = [item for item in path_value.split(os.pathsep) if item]
    kept = [item for item in entries if not _looks_like_python(item)]
    base["PATH"] = os.pathsep.join(kept)

    return (base, removed_vars, len(entries) - len(kept))


def _looks_like_python(entry: str) -> bool:
    lowered = entry.lower()
    return any(marker in lowered for marker in PYTHON_PATH_MARKERS)


def find_executable(dist_root: Path) -> Path | None:
    """Üretilmiş paketin çalıştırılabilirini bulur (en yeni sürüm)."""
    candidates = sorted(dist_root.glob("sonar-analyzer-*/sonar-analyzer.exe"))
    return candidates[-1] if candidates else None


def check(executable: Path) -> CleanEnvResult:
    """Paketi temizlenmiş ortamda çalıştırır ve sonucu döner."""
    env, removed_vars, removed_paths = scrub_environment()
    result = CleanEnvResult(
        executable=str(executable),
        removed_env_vars=removed_vars,
        removed_path_entries=removed_paths,
        remaining_path_entries=len([x for x in env.get("PATH", "").split(os.pathsep) if x]),
        python_on_path=_python_reachable(env),
        machine={"platform": platform.platform()},
    )

    version = subprocess.run(
        [str(executable), "--version"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(executable.parent),
    )
    result.version_reported = version.stdout.strip() or version.stderr.strip()

    completed = subprocess.run(
        [str(executable), "--self-check"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(executable.parent),
    )
    result.self_check_exit = completed.returncode
    result.self_check_lines = [
        line.strip()
        for line in (completed.stdout + completed.stderr).splitlines()
        if line.strip() and not line.startswith("20")  # log satirlari haric
    ]
    return result


def _python_reachable(env: dict[str, str]) -> bool:
    """Temizlenen ortamda hâlâ bir `python` bulunabiliyor mu?"""
    for entry in env.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        for name in ("python.exe", "python3.exe"):
            try:
                if (Path(entry) / name).is_file():
                    return True
            except OSError:
                # WindowsApps altindaki "app execution alias" girdileri
                # erisildiginde WinError 1920 veriyor; erisilemeyen bir yol
                # zaten calistirilabilir bir Python degildir.
                continue
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Temiz ortam acilis kontrolu (F6-005)")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--executable", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    executable = args.executable or find_executable(args.dist)
    if executable is None or not executable.is_file():
        print(
            f"Paket bulunamadi: {args.dist}\nOnce uretin: python tools/build_package.py",
            file=sys.stderr,
        )
        return 2

    result = check(executable)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")

    print(f"calistirilan: {result.executable}")
    print(f"silinen PYTHON* degiskeni: {len(result.removed_env_vars)}")
    print(f"PATH'ten cikarilan dizin: {result.removed_path_entries}")
    print(f"ortamda python bulunuyor mu: {'EVET' if result.python_on_path else 'hayir'}")
    print(f"surum: {result.version_reported}")
    for line in result.self_check_lines:
        print(f"  {line}")
    print("sonuc: " + ("TAMAM" if result.ok else "BASARISIZ"))
    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
