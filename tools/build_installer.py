"""Windows installer üretimi — `F6-007`.

Kabul: **Uygulama, kısayol ve kaldırma girdisi beklenen konumdadır.**

`F6-004` paketi üretiyor; bu araç o paketi **kurulabilir** hâle getiriyor.
NSIS betiği (`packaging/installer.nsi`) sürümü ve kaynak dizini dışarıdan
alır, böylece `VERSION` tek doğruluk kaynağı olarak kalır ve installer'ın
adı, gösterdiği sürüm ve kurduğu paket birbirinden ayrışamaz.

Kurulum **kullanıcı bazındadır** (`HKCU` + `LOCALAPPDATA`): yönetici
hakkı istemez. Yönetici gerektiren bir kurulum, kullanıcının kendi
makinesinde deneyemediği bir kurulumdur.

NSIS kurulu değilse araç **açık bir hata** verir ve nereden kurulacağını
söyler; sessizce "installer üretilmedi" demek, dağıtım hattında eksik bir
adımı gizlemek olurdu.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "packaging" / "installer.nsi"
VERSION_FILE = ROOT / "VERSION"
DEFAULT_DIST = ROOT / "dist"

#: NSIS'in bilinen kurulum yerleri (PATH'te yoksa buralara bakilir).
NSIS_CANDIDATES: tuple[str, ...] = (
    r"C:\Program Files (x86)\NSIS\makensis.exe",
    r"C:\Program Files\NSIS\makensis.exe",
)


@dataclass
class InstallerResult:
    """Installer üretiminin kaydı."""

    version: str
    succeeded: bool
    exit_code: int
    installer_path: str = ""
    installer_bytes: int = 0
    source_dir: str = ""
    compiler: str = ""
    log_tail: list[str] = field(default_factory=lambda: [])


def find_makensis() -> Path | None:
    """NSIS derleyicisini bulur: önce `PATH`, sonra bilinen konumlar."""
    found = shutil.which("makensis")
    if found:
        return Path(found)
    for candidate in NSIS_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def find_package(dist_root: Path, version: str) -> Path | None:
    """Kurulacak paketin klasörü; yoksa `None`."""
    candidate = dist_root / f"sonar-analyzer-{version}"
    return candidate if (candidate / "sonar-analyzer.exe").is_file() else None


def build_installer(
    *,
    dist_root: Path = DEFAULT_DIST,
    output: Path | None = None,
) -> InstallerResult:
    """Installer'ı üretir."""
    version = read_version()
    compiler = find_makensis()
    if compiler is None:
        return InstallerResult(
            version=version,
            succeeded=False,
            exit_code=127,
            log_tail=[
                "NSIS bulunamadi (makensis).",
                "Kurulum: https://nsis.sourceforge.io/Download",
            ],
        )

    source = find_package(dist_root, version)
    if source is None:
        return InstallerResult(
            version=version,
            succeeded=False,
            exit_code=2,
            compiler=str(compiler),
            log_tail=[
                f"Paket bulunamadi: {dist_root / f'sonar-analyzer-{version}'}",
                "Once uretin: python tools/build_package.py",
            ],
        )

    target = output or (dist_root / f"sonar-analyzer-{version}-setup.exe")
    command = [
        str(compiler),
        f"/DAPP_VERSION={version}",
        f"/DSOURCE_DIR={source}",
        f"/DOUT_FILE={target}",
        str(SCRIPT),
    ]
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output_text = completed.stdout + completed.stderr

    return InstallerResult(
        version=version,
        succeeded=completed.returncode == 0 and target.is_file(),
        exit_code=completed.returncode,
        installer_path=str(target),
        installer_bytes=target.stat().st_size if target.is_file() else 0,
        source_dir=str(source),
        compiler=str(compiler),
        log_tail=output_text.splitlines()[-12:],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Windows installer uretir (F6-007)")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    result = build_installer(dist_root=args.dist, output=args.output)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")

    print(f"surum: {result.version}")
    if result.compiler:
        print(f"derleyici: {result.compiler}")
    if result.succeeded:
        print(f"installer: {result.installer_path}")
        print(f"boyut: {result.installer_bytes} bayt")
        print("sonuc: TAMAM")
        return 0

    for line in result.log_tail:
        print(f"  {line}", file=sys.stderr)
    print(f"sonuc: BASARISIZ (cikis kodu {result.exit_code})", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
