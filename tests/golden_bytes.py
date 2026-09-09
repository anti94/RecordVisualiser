"""Golden `.bin` bayt dizileri — testler arası paylaşılan üretici.

Bu bir test dosyası değildir (pytest'in `test_*` deseniyle eşleşmez);
`docs/format/fixture-valid-8records.md` §1'deki deterministik formülleri
tek yerde tutar. `F2-016` bu formülü kalıcı `.bin` dosyası üreten bir
komut satırı aracına taşıyacaktır; o zamana kadar testler burayı kullanır.
"""

from __future__ import annotations

import zlib

from sonar_analyzer.io.profile_a_format import (
    DATA_RECORD_V1,
    DATA_RECORD_V2,
    FILE_HEADER_V1,
    FILE_HEADER_V2,
)

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


def build_gap_fixture() -> bytes:
    """`docs/format/timing-and-naming.md` §4 örneği: `sequence_no = 5` kayıp.

    Fiziksel sıra 0..7 yazılır ama sequence_no'lar 0,1,2,3,4,6,7,8'dir.
    Dosya yine 8 kayıt / 544 bayttır.
    """
    header = FILE_HEADER_V1.pack(b"SONARBIN", 1, 32, 64, 125_000, CHANNEL_COUNT, START_TIME_UTC_NS)
    written_sequences = (0, 1, 2, 3, 4, 6, 7, 8)
    body = bytearray(header)
    for n in written_sequences:
        body += DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * 125_000,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
        )
    return bytes(body)


def build_duplicate_sequence_fixture() -> bytes:
    """`F2-011`: fiziksel sıradaki 3. kayıt (index 3), önceki kayıtla aynı
    `sequence_no = 2`'yi tekrarlar. Diğer alanlar index 3'ün kendi
    formülüyle yazılır — yalnız `sequence_no` ve `elapsed_us` sabitlenir.

    Fiziksel sequence_no dizisi: 0, 1, 2, 2, 4, 5, 6, 7.
    """
    header = FILE_HEADER_V1.pack(b"SONARBIN", 1, 32, 64, 125_000, CHANNEL_COUNT, START_TIME_UTC_NS)
    body = bytearray(header)
    physical_sequences = (0, 1, 2, 2, 4, 5, 6, 7)
    for n in physical_sequences:
        body += DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * 125_000,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
        )
    return bytes(body)


def build_out_of_order_fixture() -> bytes:
    """`F2-011`: fiziksel sırada `sequence_no` geri gider (reset/bozulma).

    Fiziksel sequence_no dizisi: 0, 1, 2, 3, 1, 5, 6, 7 — index 4'te (fiziksel
    5. kayıt) sequence_no önceki kayıttan (3) küçüktür (1).
    """
    header = FILE_HEADER_V1.pack(b"SONARBIN", 1, 32, 64, 125_000, CHANNEL_COUNT, START_TIME_UTC_NS)
    body = bytearray(header)
    physical_sequences = (0, 1, 2, 3, 1, 5, 6, 7)
    for n in physical_sequences:
        body += DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * 125_000,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
        )
    return bytes(body)


def build_valid_v2_fixture(record_count: int = 8) -> bytes:
    """`F2-012`/`ADR-011-crc.md` §2.3: v1 ile aynı formüller, CRC'li 68B kayıt.

    Her kaydın `record_crc32` alanı, CRC hariç 64 baytın CRC-32'sidir
    (`F2-013`'ün kapsamı tam algoritmayı sabitler; burada yalnız decoder
    seçiminin CRC alanını doğru şekilde çözdüğünü göstermek için makul bir
    değer yazılır). Header'ın `header_crc32` alanı da aynı yöntemle,
    CRC hariç ilk 32 baytın CRC-32'sidir.
    """
    header_body = FILE_HEADER_V1.pack(
        b"SONARBIN", 2, 36, 68, 125_000, CHANNEL_COUNT, START_TIME_UTC_NS
    )
    header_crc32 = zlib.crc32(header_body)
    header = FILE_HEADER_V2.pack(
        b"SONARBIN", 2, 36, 68, 125_000, CHANNEL_COUNT, START_TIME_UTC_NS, header_crc32
    )
    body = bytearray(header)
    for n in range(record_count):
        record_body = DATA_RECORD_V1.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * 125_000,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
        )
        record_crc32 = zlib.crc32(record_body)
        body += DATA_RECORD_V2.pack(
            f"Data{n:05d}".encode("ascii"),
            n,
            n * 125_000,
            *sensor_values(n),
            bit_status_for(n),
            tx_status_for(n),
            record_crc32,
        )
    return bytes(body)


def build_name_mismatch_fixture() -> bytes:
    """docs/format/fixture-corrupt.md K-06: sequence_no=2'nin name alani
    Data00099 yapilir, diger alanlar dokunulmaz.

    "Data00099" 9 karakterdir; alan char[12] oldugu icin sonuna 3 sifir
    bayt eklenir (b"Data00099" + bytes(3) = 12 bayt) — literal \\x00
    kacis dizisi yerine bytes(3) kullanildi, cunku bu ortamdaki kabuk
    araci bazi \\xNN dizilerini kaynak dosyaya yazmadan once kendi
    yorumluyor ve gercek NUL bayt sizdiriyordu (once bu yuzden bozuk bir
    dosya uretilmisti).
    """
    buffer = bytearray(build_valid_fixture())
    record_offset = 32 + 2 * 64  # sequence_no = 2
    buffer[record_offset : record_offset + 12] = b"Data00099" + bytes(3)
    return bytes(buffer)
