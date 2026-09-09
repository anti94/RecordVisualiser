"""Kesik, bozuk ve sıra boşluklu fixture yazıcısı — `F2-017`.

`docs/format/fixture-corrupt.md`'deki beş senaryoyu (K-01, K-02, K-03,
K-05, K-06) üretir. Taban dosya `tools/make_fixture.py::build_valid_fixture()`
çıktısıdır; her senaryo o dosyadan **tek bir kusurla** türetilir (F0-010
ilkesi) — böylece gözlenen fark tek bir nedene bağlanabilir.

`K-04` (CRC hatası) burada **yok**: Profil A sürüm 2 (CRC destekli) gerektirir,
`F2-018`'in kapsamındadır.

Kullanım:
    python tools/make_corrupt_fixtures.py
    python tools/make_corrupt_fixtures.py --out-dir tests/fixtures
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.make_fixture import (  # noqa: E402 -- sys.path kurulumundan sonra
    CHANNEL_COUNT,
    PERIOD_US,
    START_TIME_UTC_NS,
    bit_status_for,
    build_valid_fixture,
    sensor_values,
    tx_status_for,
)

from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, FILE_HEADER_V1  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "tests" / "fixtures"

#: docs/format/fixture-corrupt.md — (dosya adı, üretici, beklenen SHA-256).
_VERSION_FIELD_OFFSET = 8


def build_k01_truncated_header() -> bytes:
    """K-01: `valid_8records.bin`'in ilk 20 baytı — header 32 bayttan kısa."""
    return build_valid_fixture()[:20]


def build_k02_truncated_last_record() -> bytes:
    """K-02: ilk 524 bayt — son kayıt 44/64 bayt olarak yarım kalır."""
    return build_valid_fixture()[:524]


def build_k03_gap_missing_record() -> bytes:
    """K-03: `sequence_no = 5` yazılmadan 8 kayıt (0,1,2,3,4,6,7,8)."""
    header = FILE_HEADER_V1.pack(
        b"SONARBIN", 1, 32, 64, PERIOD_US, CHANNEL_COUNT, START_TIME_UTC_NS
    )
    written_sequences = (0, 1, 2, 3, 4, 6, 7, 8)
    body = bytearray(header)
    for n in written_sequences:
        body += DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * PERIOD_US,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
        )
    return bytes(body)


def build_k05_unsupported_version() -> bytes:
    """K-05: `version` alanı (offset 8) `1 → 99`."""
    buffer = bytearray(build_valid_fixture())
    buffer[_VERSION_FIELD_OFFSET] = 99
    return bytes(buffer)


def build_k06_name_index_mismatch() -> bytes:
    """K-06: `sequence_no = 2` olan kaydın `name` alanı `Data00099` yapılır."""
    buffer = bytearray(build_valid_fixture())
    record_offset = 32 + 2 * 64
    buffer[record_offset : record_offset + 12] = b"Data00099" + bytes(3)
    return bytes(buffer)


#: (dosya adı, üretici fonksiyon, beklenen SHA-256) — docs/format/fixture-corrupt.md.
SCENARIOS: tuple[tuple[str, Callable[[], bytes], str], ...] = (
    (
        "truncated_header.bin",
        build_k01_truncated_header,
        "49c4c7a46803a28007700129a74544351fc0c6a14bc7dc89cf3930f4bff74651",
    ),
    (
        "truncated_last_record.bin",
        build_k02_truncated_last_record,
        "ea294eba3f1f5ffcbf2fcdfd13c2fec9f4d3163bb7084122732c90a01fbd28ad",
    ),
    (
        "gap_missing_record.bin",
        build_k03_gap_missing_record,
        "0ddd96308c58d7807004029fa4dcf19f20034eb2294ab2ec5274210c336bcaab",
    ),
    (
        "unsupported_version.bin",
        build_k05_unsupported_version,
        "cc1f6eeb520486415e13b1e8f2c00a669ea1a5a712630d6abc2e4596ebd27bfe",
    ),
    (
        "name_index_mismatch.bin",
        build_k06_name_index_mismatch,
        "b1f807cf1bbea070273ce48d9d2b45d06a402a46241cd1bd576b290e0cb14a84",
    ),
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="K-01/K-02/K-03/K-05/K-06 bozuk fixture'larini yazar."
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for filename, builder, expected_sha256 in SCENARIOS:
        data = builder()
        out_path = args.out_dir / filename
        out_path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        status = "OK" if digest == expected_sha256 else "UYUSMUYOR"
        print(f"{out_path}: {len(data)} bayt, sha256={digest} [{status}]")
        if digest != expected_sha256:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
