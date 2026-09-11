"""Tek komutluk Windows paketi üretimi — `F6-004`.

Kabul: **Komut sürümlü çıktı klasörü ve build logu üretir.**

Paketleme elle çalıştırılan bir dizi komut olarak kalırsa, üretilen paketin
hangi kaynaktan ve hangi araç sürümleriyle çıktığı kimsenin elinde olmaz.
Bu araç akışı tek komuta indirir ve **her koşuyu kaydeder**:

* çıktı `dist/sonar-analyzer-<surum>/` altına, **sürümlü** bir klasöre
  yazılır — iki farklı sürümün paketleri birbirinin üzerine yazmaz,
* PyInstaller'ın bütün çıktısı bir **build logu**na (`build.log`) alınır,
* koşunun özeti (sürüm, araç sürümleri, süre, dosya sayısı, çıkış kodu)
  makine tarafından okunabilir bir manifeste (`build-manifest.json`)
  yazılır.

Başarısız koşu da kaydedilir. Yalnız başarılı koşuları yazan bir akış,
"neden bozuldu" sorusunu cevaplayamaz.

Kullanım::

    .venv\\Scripts\\python.exe tools\\build_package.py
    .venv\\Scripts\\python.exe tools\\build_package.py --clean
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "sonar-analyzer.spec"
VERSION_FILE = ROOT / "VERSION"

DEFAULT_DIST = ROOT / "dist"
DEFAULT_WORK = ROOT / "build" / "package"

BUILD_LOG_NAME = "build.log"
MANIFEST_NAME = "build-manifest.json"


@dataclass
class BuildResult:
    """Bir paket üretim koşusunun kaydı."""

    version: str
    succeeded: bool
    exit_code: int
    started_utc: str
    duration_seconds: float
    output_dir: str
    build_log: str
    tools: dict[str, str] = field(default_factory=lambda: {})
    machine: dict[str, str] = field(default_factory=lambda: {})
    file_count: int = 0
    total_bytes: int = 0


def read_version() -> str:
    """Sürüm tek kaynaktan: depo kökündeki ``VERSION``."""
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def tool_versions() -> dict[str, str]:
    """Üretimde rol alan araçların sürümleri.

    Manifeste yazılır çünkü `F6-010` aynı girdilerle üretimi
    karşılaştıracak; araç sürümü değiştiyse hash farkının nedeni budur ve
    bunun sonradan bilinebilmesi gerekir.
    """
    versions = {"python": platform.python_version()}
    try:
        import PyInstaller  # pyright: ignore[reportMissingTypeStubs]

        versions["pyinstaller"] = str(PyInstaller.__version__)
    except ImportError:
        versions["pyinstaller"] = "kurulu degil"
    return versions


def measure_output(path: Path) -> tuple[int, int]:
    """Üretilen klasördeki dosya sayısı ve toplam bayt."""
    if not path.is_dir():
        return (0, 0)
    files = [item for item in path.rglob("*") if item.is_file()]
    return (len(files), sum(item.stat().st_size for item in files))


def build(
    *,
    dist_root: Path = DEFAULT_DIST,
    work_root: Path = DEFAULT_WORK,
    clean: bool = False,
    runner: Callable[[list[str]], tuple[int, str]] | None = None,
) -> BuildResult:
    """Paketi üretir ve koşuyu kaydeder.

    `runner` testler için enjekte edilebilir: gerçek PyInstaller koşusu
    dakikalar sürer ve akışın kendisini sınamak için gerekmez.
    """
    version = read_version()
    output_dir = dist_root / f"sonar-analyzer-{version}"
    dist_root.mkdir(parents=True, exist_ok=True)

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    log_path = dist_root / BUILD_LOG_NAME
    started = datetime.now(timezone.utc)
    clock = perf_counter()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(dist_root),
        "--workpath",
        str(work_root),
        str(SPEC),
    ]

    execute = runner if runner is not None else _run_subprocess
    exit_code, output = execute(command)

    duration = perf_counter() - clock
    # Log HER DURUMDA yazilir; basarisiz kosu da kaydedilmeli.
    log_path.write_text(output, encoding="utf-8", errors="replace")

    count, total = measure_output(output_dir)
    result = BuildResult(
        version=version,
        succeeded=exit_code == 0 and output_dir.is_dir(),
        exit_code=exit_code,
        started_utc=started.isoformat(timespec="seconds"),
        duration_seconds=round(duration, 2),
        output_dir=str(output_dir),
        build_log=str(log_path),
        tools=tool_versions(),
        machine={"platform": platform.platform(), "processor": platform.processor()},
        file_count=count,
        total_bytes=total,
    )

    manifest = dist_root / MANIFEST_NAME
    manifest.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
    return result


def _run_subprocess(command: list[str]) -> tuple[int, str]:
    """PyInstaller'ı çalıştırır; çıktısını (stdout+stderr) birlikte döner."""
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return (completed.returncode, completed.stdout + completed.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Windows paketini uretir (F6-004)")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="ayni surumun onceki ciktisini silerek bastan uretir",
    )
    args = parser.parse_args(argv)

    result = build(dist_root=args.dist, work_root=args.work, clean=args.clean)

    print(f"surum: {result.version}")
    print(f"cikti: {result.output_dir}")
    print(f"log:   {result.build_log}")
    print(f"sure:  {result.duration_seconds} s")
    if result.succeeded:
        print(f"dosya: {result.file_count} adet, {result.total_bytes} bayt")
        print("sonuc: TAMAM")
        return 0

    print(f"sonuc: BASARISIZ (cikis kodu {result.exit_code}) — ayrinti: {result.build_log}")
    return 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
