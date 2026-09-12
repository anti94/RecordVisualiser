"""Klasör indeksi kurma süresi ölçümü — `F7-035`.

Soru şu: 10 dakikalık bir kayıt 1.200 dosya taşıyor; bu klasörün indeksi
kurulurken ilk açılış bütçesi aşılıyor mu?

Ölçüm iki parçaya ayrılır, çünkü maliyetin iki bileşeni var ve ikisi
farklı ölçekleniyor:

* **Dosya sayısı maliyeti** — dizin taraması, `stat`, ad ayrıştırma.
  Dosya boyutundan bağımsızdır. 1.200 küçük dosyayla ölçülür.
* **Dosya başına okuma maliyeti** — her dosyanın başlığını ve frame
  başlıklarını çözmek. Dosya boyutuna bağlıdır. Gerçek boyutlu
  (32 × 820, 2 MiB) az sayıda dosyayla ölçülür.

İkisi birleştirilip 1.200 dosyaya **çıkarım** yapılır. Çıkarım olduğu
raporda açıkça yazar: 1.200 tam boyutlu dosya 2,4 GiB tutar ve her
ölçümde onu yazmak diskle ölçüm yapmak olurdu, indeksle değil.

Kullanım::

    python tools/profile_c_index_benchmark.py --out docs/perf/results/profile-c-index.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from tools.profile_c_writer import WriteSpec, write_recording  # noqa: E402

from sonar_analyzer.io.decoders.profile_c import decode_file  # noqa: E402
from sonar_analyzer.io.decoders.profile_c_folder import Stream, discover  # noqa: E402
from sonar_analyzer.io.index.profile_c_index import (  # noqa: E402
    FileEntry,
    FolderIndex,
    folder_fingerprint,
    write_index,
)
from sonar_analyzer.io.schema.loader import load_text  # noqa: E402
from sonar_analyzer.io.schema.model import Schema  # noqa: E402
from sonar_analyzer.io.schema.runtime import fingerprint  # noqa: E402

EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"

#: Tavan: 10 dakikalik kayit, akim basina 600 dosya (D-26).
CEILING_SECONDS = 600

#: Bolum 11 acilis butcesi. Klasor indeksi bunun bir parcasi olmali.
OPEN_BUDGET_S = 3.0


def _schema(sensors: int, samples: int) -> Schema:
    text = EXAMPLE.read_text(encoding="utf-8")
    return load_text(
        text.replace("sensor_count = 32", f"sensor_count = {sensors}").replace(
            "frame_samples = 820", f"frame_samples = {samples}"
        )
    )


@dataclass(frozen=True)
class Phase:
    """Ölçümün bir aşaması."""

    name: str
    seconds: float
    files: int

    @property
    def per_file_ms(self) -> float:
        return self.seconds / self.files * 1000 if self.files else 0.0


def _build_index(folder_path: Path, schema: Schema, *, decode: bool) -> tuple[Phase, Phase]:
    """Klasörü tarar ve indeksi kurar; tarama ile okuma ayrı ölçülür."""
    started = perf_counter()
    folder = discover(folder_path)
    scan = Phase("tarama", perf_counter() - started, folder.file_count)

    started = perf_counter()
    entries: dict[str, tuple[FileEntry, ...]] = {}
    for stream in Stream:
        listing = folder.listing(stream)
        if not listing.present:
            continue
        items: list[FileEntry] = []
        for item in listing.files:
            frame_count = 0
            start_ns: int | None = None
            end_ns: int | None = None
            if decode:
                decoded = decode_file(schema, item.path.read_bytes(), verify_crc=False)
                frame_count = decoded.frame_count
                if decoded.frames:
                    start_ns = decoded.frames[0].timestamp_ns
                    end_ns = decoded.frames[-1].timestamp_ns
            items.append(
                FileEntry(
                    counter=item.counter,
                    name=item.path.name,
                    size_bytes=item.size_bytes,
                    frame_count=frame_count,
                    start_ns=start_ns,
                    end_ns=end_ns,
                )
            )
        entries[stream.value] = tuple(items)

    index = FolderIndex(
        fingerprint=folder_fingerprint(folder),
        schema_fingerprint=fingerprint(schema),
        entries=entries,
    )
    write_index(folder, index)
    read = Phase("okuma+yazma", perf_counter() - started, folder.file_count)
    return scan, read


def run(workspace: Path, *, full_seconds: int = 20) -> dict[str, object]:
    """Iki ölçümü koşturur ve tavana çıkarım yapar."""
    small_root = workspace / "kucuk"
    small_root.mkdir(parents=True, exist_ok=True)
    small_spec = WriteSpec(seconds=CEILING_SECONDS, sensors=2, samples=4)
    small_folder = write_recording(small_root, small_spec)
    small_scan, small_read = _build_index(
        small_folder, _schema(small_spec.sensors, small_spec.samples), decode=True
    )

    full_root = workspace / "tam"
    full_root.mkdir(parents=True, exist_ok=True)
    full_spec = WriteSpec(seconds=full_seconds, sensors=32, samples=820)
    full_folder = write_recording(full_root, full_spec)
    full_scan, full_read = _build_index(
        full_folder, _schema(full_spec.sensors, full_spec.samples), decode=True
    )

    ceiling_files = CEILING_SECONDS * 2
    projected_s = (
        small_scan.per_file_ms * ceiling_files + full_read.per_file_ms * ceiling_files
    ) / 1000

    return {
        "ceiling_files": ceiling_files,
        "open_budget_s": OPEN_BUDGET_S,
        "small": {
            "files": small_scan.files,
            "file_bytes": small_spec.file_bytes,
            "scan_s": round(small_scan.seconds, 4),
            "scan_per_file_ms": round(small_scan.per_file_ms, 4),
            "read_s": round(small_read.seconds, 4),
            "read_per_file_ms": round(small_read.per_file_ms, 4),
        },
        "full": {
            "files": full_scan.files,
            "file_bytes": full_spec.file_bytes,
            "scan_s": round(full_scan.seconds, 4),
            "scan_per_file_ms": round(full_scan.per_file_ms, 4),
            "read_s": round(full_read.seconds, 4),
            "read_per_file_ms": round(full_read.per_file_ms, 4),
        },
        "projection": {
            "basis": (
                "kucuk olcumden dosya sayisi maliyeti (tarama), "
                "tam boyutlu olcumden dosya basina okuma maliyeti"
            ),
            "projected_s": round(projected_s, 3),
            "within_budget": projected_s <= OPEN_BUDGET_S,
            "caveat": (
                f"1.200 tam boyutlu dosya {ceiling_files * 2_099_200 / 1024**3:.2f} GiB tutar; "
                f"her olcumde yazmak diskle olcum yapmak olurdu, indeksle degil"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profil C klasor indeksi olcumu")
    parser.add_argument("--out", type=Path, default=None, help="JSON rapor yolu")
    parser.add_argument("--full-seconds", type=int, default=20, help="tam boyutlu dosya sayisi")
    parser.add_argument("--keep", action="store_true", help="uretilen kayitlari silme")
    args = parser.parse_args(argv)

    workspace = Path(tempfile.mkdtemp(prefix="profile-c-bench-"))
    try:
        report = run(workspace, full_seconds=args.full_seconds)
    finally:
        if not args.keep:
            shutil.rmtree(workspace, ignore_errors=True)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nyazildi: {args.out}")

    projection = report["projection"]
    assert isinstance(projection, dict)
    return 0 if projection["within_budget"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
