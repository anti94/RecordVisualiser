"""Kesik, bozuk, sıra boşluklu ve CRC hatalı fixture yazıcısı — `F2-017`, `F2-018`.

`docs/format/fixture-corrupt.md`'deki altı senaryoyu (K-01, K-02, K-03,
K-04, K-05, K-06) üretir. Taban dosya `tools/make_fixture.py`'deki
`build_valid_fixture()`/`build_valid_v2_fixture()` çıktısıdır; her senaryo
o dosyadan **tek bir kusurla** türetilir (F0-010 ilkesi) — böylece gözlenen
fark tek bir nedene bağlanabilir.

`K-04` (CRC hatası, `F2-018`) Profil A sürüm 2 (CRC destekli) gerektirir;
ayrıca kabul kriterinin ("geçerli ve tek byte bozulmuş dosya farklı
doğrulama sonucu verir") karşılaştırma tarafı için bozulmamış
`valid_8records_v2.bin` da yazılır.

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
    HEADER_SIZE_V2,
    PERIOD_US,
    RECORD_SIZE_V2,
    START_TIME_UTC_NS,
    bit_status_for,
    build_valid_fixture,
    build_valid_v2_fixture,
    sensor_values,
    tx_status_for,
)

from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, FILE_HEADER_V1  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "tests" / "fixtures"

#: docs/format/fixture-corrupt.md — (dosya adı, üretici, beklenen SHA-256).
_VERSION_FIELD_OFFSET = 8
#: K-04: Data00003'un CH0 alaninin ilk bayti.
#: offset = 12 (name) + 4 (sequence_no) + 8 (elapsed_us).
_CH0_FIRST_BYTE_OFFSET_IN_RECORD = 24


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


def build_valid_v2_8records() -> bytes:
    """K-04'ün bozulmamış tabanı: geçerli CRC'li 8 kayıt (580 bayt)."""
    return build_valid_v2_fixture()


def build_k04_crc_error() -> bytes:
    """K-04: `Data00003`'ün CH0 alanının ilk baytı `0x00 → 0x01`; CRC alanı değiştirilmez."""
    buffer = bytearray(build_valid_v2_fixture())
    record_offset = HEADER_SIZE_V2 + 3 * RECORD_SIZE_V2
    corrupt_at = record_offset + _CH0_FIRST_BYTE_OFFSET_IN_RECORD
    buffer[corrupt_at] ^= 0x01
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
    (
        "valid_8records_v2.bin",
        build_valid_v2_8records,
        "57681d96de5eedf22b86f3ca2ce1e359a721bb0680cc01f69d6c74a658c7bf4f",
    ),
    (
        "crc_error.bin",
        build_k04_crc_error,
        "d23348d74ce425532c534713fa83fa875d91d185b335f2298f067f08051f8aaf",
    ),
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="K-01/K-02/K-03/K-04/K-05/K-06 bozuk fixture'larini yazar."
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
