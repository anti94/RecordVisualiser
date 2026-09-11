"""Aynı girdilerle paket üretimini karşılaştırır — `F6-010`.

Kabul: **Araç sürümleri ve hash farkları kaydedilir; deterministik
olmayan alanlar açıklanır.**

"Aynı kaynaktan aynı paket" sözü, verilmeden önce **ölçülmelidir**.
Bu araç aynı girdilerle iki kez paket üretir ve çıktıları dosya dosya
karşılaştırır:

* her iki tarafta da bulunan ama **hash'i farklı** dosyalar,
* yalnız bir tarafta bulunan dosyalar,
* kullanılan araç sürümleri (fark varsa nedeni budur).

Amaç "bit bit aynı" çıkmasını sağlamak değil — PyInstaller'ın çıktısı
zaman damgası ve derleme yolu gibi alanlar taşır ve tam belirlenimlilik
ayrı bir mühendislik işidir. Amaç **farkın ne olduğunu bilmek**: hangi
dosyalar neden değişiyor, yazılı olsun ki bir gün beklenmedik bir dosya
değiştiğinde fark edilsin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_package import build, read_version, tool_versions  # noqa: E402

DEFAULT_REPORT = ROOT / "docs" / "packaging" / "results" / "build-reproducibility.json"

#: Farkin beklendigi dosyalar ve NEDENI. Beklenen bir fark, aciklanmis
#: bir farktir; listede olmayan bir fark incelenmelidir.
EXPECTED_DIFFERENCES: dict[str, str] = {
    "sonar-analyzer.exe": (
        "PyInstaller bootloader'a derleme zamani ve gomulu arsiv tablosunu "
        "yaziyor; ikisi de kosudan kosuya degisiyor."
    ),
    "base_library.zip": "ZIP girdileri derleme zaman damgasi tasiyor.",
}


@dataclass
class FileDifference:
    """Tek bir dosyanın iki koşu arasındaki durumu."""

    path: str
    status: str  # "farkli" | "yalniz_ilk" | "yalniz_ikinci"
    first_sha256: str = ""
    second_sha256: str = ""
    expected: bool = False
    reason: str = ""


@dataclass
class ReproducibilityReport:
    """İki üretimin karşılaştırması."""

    version: str
    tools: dict[str, str] = field(default_factory=lambda: {})
    total_files: int = 0
    identical_files: int = 0
    differences: list[FileDifference] = field(default_factory=lambda: [])

    @property
    def unexplained(self) -> list[FileDifference]:
        """Açıklanmamış farklar — asıl ilgilenilmesi gerekenler."""
        return [item for item in self.differences if not item.expected]

    @property
    def ok(self) -> bool:
        """Fark olabilir; **açıklanmamış** fark olmamalı."""
        return self.total_files > 0 and not self.unexplained


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _snapshot(root: Path) -> dict[str, str]:
    """Klasördeki her dosyanın göreli yolu → hash."""
    return {
        str(item.relative_to(root)).replace("\\", "/"): _hash(item)
        for item in sorted(root.rglob("*"))
        if item.is_file()
    }


def _explain(relative_path: str) -> tuple[bool, str]:
    """Fark bekleniyor mu, neden?"""
    name = Path(relative_path).name
    reason = EXPECTED_DIFFERENCES.get(name)
    return (reason is not None, reason or "")


def compare(first: dict[str, str], second: dict[str, str]) -> list[FileDifference]:
    """İki anlık görüntüyü karşılaştırır."""
    differences: list[FileDifference] = []

    for path in sorted(set(first) | set(second)):
        left, right = first.get(path), second.get(path)
        if left == right:
            continue
        if left is None:
            differences.append(
                FileDifference(path=path, status="yalniz_ikinci", second_sha256=right or "")
            )
            continue
        if right is None:
            differences.append(FileDifference(path=path, status="yalniz_ilk", first_sha256=left))
            continue
        expected, reason = _explain(path)
        differences.append(
            FileDifference(
                path=path,
                status="farkli",
                first_sha256=left,
                second_sha256=right,
                expected=expected,
                reason=reason,
            )
        )
    return differences


def run_comparison(work_root: Path) -> ReproducibilityReport:
    """Aynı girdilerle iki paket üretip karşılaştırır."""
    version = read_version()
    snapshots: list[dict[str, str]] = []

    for index in (1, 2):
        dist = work_root / f"kosu{index}"
        result = build(dist_root=dist, work_root=work_root / f"is{index}")
        if not result.succeeded:
            raise RuntimeError(f"{index}. uretim basarisiz (cikis kodu {result.exit_code})")
        snapshots.append(_snapshot(Path(result.output_dir)))

    first, second = snapshots
    differences = compare(first, second)
    return ReproducibilityReport(
        version=version,
        tools=tool_versions(),
        total_files=len(set(first) | set(second)),
        identical_files=sum(1 for path, value in first.items() if second.get(path) == value),
        differences=differences,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Iki uretimi karsilastirir (F6-010)")
    parser.add_argument("--work", type=Path, default=ROOT / "build" / "repro")
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="karsilastirma sonrasi gecici uretimleri silme",
    )
    args = parser.parse_args(argv)

    args.work.mkdir(parents=True, exist_ok=True)
    try:
        report = run_comparison(args.work)
    finally:
        if not args.keep:
            shutil.rmtree(args.work, ignore_errors=True)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    print(f"surum: {report.version}")
    print(f"araclar: {report.tools}")
    print(f"dosya: {report.total_files}, ayni: {report.identical_files}")
    print(f"farkli: {len(report.differences)}")
    for item in report.differences:
        mark = "beklenen" if item.expected else "ACIKLANMAMIS"
        print(f"  [{mark}] {item.path} ({item.status})")
        if item.reason:
            print(f"            {item.reason}")
    print(f"rapor: {args.json}")
    print("sonuc: " + ("TAMAM" if report.ok else "ACIKLANMAMIS FARK VAR"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
