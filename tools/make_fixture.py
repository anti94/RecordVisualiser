"""Profil A geçerli örnek `.bin` fixture yazıcısı — `F2-016`.

`docs/format/fixture-valid-8records.md` §1'deki deterministik formülleri tek
yerde tutar ve kalıcı bir `.bin` dosyasına yazar. `tests/golden_bytes.py`
aynı fonksiyonları buradan içe aktarır — F2-016'dan önce bu formül testler
içinde tekrarlanıyordu; artık tek doğruluk kaynağı burasıdır.

Kullanım:
    python tools/make_fixture.py
    python tools/make_fixture.py --out path/valid_8records.bin --records 8

Öntanımlı hedef `tests/fixtures/valid_8records.bin`'dir (`.gitignore`'da
`*.bin` kuralından muaf tutulmuştur, bkz. `tests/fixtures/README.md`).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, FILE_HEADER_V1

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "valid_8records.bin"

#: docs/format/fixture-valid-8records.md §1: 2026-09-08T21:00:00.000Z
START_TIME_UTC_NS = 1_788_901_200_000_000_000
CHANNEL_COUNT = 8
PERIOD_US = 125_000

#: docs/format/fixture-valid-8records.md §6 — yalnız 8 kayıtlık öntanımlı dosya için geçerli.
VALID_8RECORDS_SHA256 = "5094b9b0bc585518cf7fa9dc372d3e997f32b59caeb156cb4c0f9ab9d039fce9"


def sensor_values(n: int) -> tuple[float, float, float, float, float, float, float, float]:
    """`docs/format/fixture-valid-8records.md` §1 formülleri."""
    return (
        100.0 + 0.5 * n,
        25.0,
        0.125 * n,
        0.0 - 0.125 * n,  # negatif sifir uretmeyen bicim (belgedeki uyari)
        1.0,
        2.5 if n % 2 == 0 else -2.5,
        10.0 + 0.25 * n,
        48.0,
    )


def bit_status_for(n: int) -> int:
    return 0x00000100 if n == 4 else 0


def tx_status_for(n: int) -> int:
    return 1 if 2 <= n <= 5 else 0


def build_valid_fixture(record_count: int = 8) -> bytes:
    """`docs/format/fixture-valid-8records.md` §1'deki formüllerden dosyayı üretir.

    `record_count != 8` verilirse artık golden SHA-256 ile eşleşmez; yalnız
    öntanımlı 8 kayıt belgedeki referans dosyadır.
    """
    header = FILE_HEADER_V1.pack(
        b"SONARBIN", 1, 32, 64, PERIOD_US, CHANNEL_COUNT, START_TIME_UTC_NS
    )
    body = bytearray(header)
    for n in range(record_count):
        body += DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * PERIOD_US,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
        )
    return bytes(body)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gecerli 8 kayitlik ornek .bin fixture yazar.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Cikti dosyasi yolu")
    parser.add_argument("--records", type=int, default=8, help="Kayit sayisi (ontanimli: 8)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    data = build_valid_fixture(args.records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"{args.out}: {len(data)} bayt, sha256={digest}")
    if args.records == 8 and digest != VALID_8RECORDS_SHA256:
        print("UYARI: sekiz kayitlik golden SHA-256 ile eslesmiyor!", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
