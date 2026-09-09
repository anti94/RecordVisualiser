"""Golden `.bin` bayt dizileri — testler arası paylaşılan üretici.

Bu bir test dosyası değildir (pytest'in `test_*` deseniyle eşleşmez);
`docs/format/fixture-valid-8records.md` §1'deki deterministik formülleri
tek yerde tutar. `F2-016` bu formülü kalıcı `.bin` dosyası üreten bir
komut satırı aracına taşıyacaktır; o zamana kadar testler burayı kullanır.
"""

from __future__ import annotations

from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, FILE_HEADER_V1

#: docs/format/fixture-valid-8records.md §1: 2026-09-08T21:00:00.000Z
START_TIME_UTC_NS = 1_788_901_200_000_000_000
CHANNEL_COUNT = 8

#: docs/format/fixture-valid-8records.md §6.
VALID_8RECORDS_SHA256 = "5094b9b0bc585518cf7fa9dc372d3e997f32b59caeb156cb4c0f9ab9d039fce9"


def sensor_values(n: int) -> tuple[float, float, float, float, float, float, float, float]:
    """docs/format/fixture-valid-8records.md §1 formülleri."""
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
    header = FILE_HEADER_V1.pack(b"SONARBIN", 1, 32, 64, 125_000, CHANNEL_COUNT, START_TIME_UTC_NS)
    body = bytearray(header)
    for n in range(record_count):
        body += DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * 125_000,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
        )
    return bytes(body)
