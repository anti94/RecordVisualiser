"""Offline bağımlılık paketleme akışı — `F6-011`.

Kabul: **Offline hedef varsa bağlantısız kurulum doğrulanır; yoksa koşul
ADR'de gerekçelenir.**

İki ayrı ihtiyaç vardır ve karıştırılmamalıdır:

* **Son kullanıcı** zaten offline'dır. `F6-007`'nin installer'ı
  kendi kendine yeter: Python, Qt ve bütün kütüphaneler paketin içindedir
  (`F6-005` bunu Python'suz bir ortamda doğruladı). Son kullanıcı için
  ayrıca bir şey yapmaya gerek yoktur.
* **Geliştirici/CI makinesi** bağlantısızsa bağımlılıkları indiremez ve
  paket hiç üretilemez. Asıl eksik budur ve bu araç onu kapatır:
  bağımlılıkların wheel'lerini tek bir klasöre indirir, böylece klasör
  kopyalanan bağlantısız bir makinede `pip install --no-index` ile ortam
  kurulabilir.

Araç bağlantı gerektirir (wheel'leri indirir); bağlantı yoksa **açık bir
hata** verir. Sessizce boş bir klasör bırakmak, offline kurulumu deneyen
kişiye o anda değil, en kötü anda haber verirdi.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "dist" / "offline-wheels"
DEFAULT_REPORT = ROOT / "docs" / "packaging" / "results" / "offline-bundle.json"

#: Paketin calismasi ve uretilmesi icin gereken ekstralar.
BUNDLED_EXTRAS: tuple[str, ...] = ("gui", "dsp", "package")


@dataclass
class OfflineBundle:
    """İndirilen wheel kümesinin kaydı."""

    succeeded: bool = False
    exit_code: int = 0
    output_dir: str = ""
    wheel_count: int = 0
    total_bytes: int = 0
    wheels: list[str] = field(default_factory=lambda: [])
    extras: list[str] = field(default_factory=lambda: [])
    python: str = ""
    platform: str = ""
    message: str = ""

    @property
    def install_command(self) -> str:
        """Bağlantısız makinede kurulum komutu."""
        return f'pip install --no-index --find-links "{self.output_dir}" "sonar-analyzer[gui,dsp]"'


def download_wheels(
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    extras: tuple[str, ...] = BUNDLED_EXTRAS,
    runner: Callable[[list[str]], tuple[int, str]] | None = None,
) -> OfflineBundle:
    """Bağımlılıkların wheel'lerini `output_dir`'a indirir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    requirement = f".[{','.join(extras)}]"

    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        requirement,
        "--dest",
        str(output_dir),
    ]

    execute = runner if runner is not None else _run_pip
    exit_code, output = execute(command)

    # Projenin KENDI wheel'i de klasore konur. `pip download` yalniz
    # bagimliliklari indirir; proje olmadan bagalantisiz makinede
    # "sonar-analyzer" paketi bulunamaz ve kurulum cozumlenemez.
    if exit_code == 0:
        exit_code, build_output = execute(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(output_dir), "."]
        )
        output += build_output

    wheels = sorted(path.name for path in output_dir.glob("*.whl"))
    archives = sorted(path.name for path in output_dir.glob("*.tar.gz"))
    everything = wheels + archives
    total = sum(path.stat().st_size for path in output_dir.iterdir() if path.is_file())

    bundle = OfflineBundle(
        succeeded=exit_code == 0 and bool(everything),
        exit_code=exit_code,
        output_dir=str(output_dir),
        wheel_count=len(everything),
        total_bytes=total,
        wheels=everything,
        extras=list(extras),
        python=platform.python_version(),
        platform=platform.platform(),
    )
    if not bundle.succeeded:
        bundle.message = output.strip().splitlines()[-1] if output.strip() else "indirme basarisiz"
    return bundle


def _run_pip(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return (completed.returncode, completed.stdout + completed.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline bagimlilik paketi hazirlar (F6-011)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    bundle = download_wheels(args.output)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(bundle), indent=2) + "\n", encoding="utf-8")

    print(f"ekstralar: {', '.join(bundle.extras)}")
    print(f"klasor: {bundle.output_dir}")
    if bundle.succeeded:
        print(f"paket: {bundle.wheel_count} adet, {bundle.total_bytes} bayt")
        print(f"baglantisiz kurulum: {bundle.install_command}")
        print("sonuc: TAMAM")
        return 0

    print(f"hata: {bundle.message}", file=sys.stderr)
    print("sonuc: BASARISIZ", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
