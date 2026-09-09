"""Golden `.bin` bayt dizileri — testler arası paylaşılan üretici.

Bu bir test dosyası değildir (pytest'in `test_*` deseniyle eşleşmez).
Geçerli 8 kayıtlık formül `F2-016` ile `tools/make_fixture.py`'ye taşındı
(tek doğruluk kaynağı orasıdır, bu modül onu içe aktarır); burada yalnız
o formülün üzerine kurulan **bozuk/anormal** senaryo üreticileri kalır.
"""

from __future__ import annotations

import sys
import zlib
from pathlib import Path

# tools/ paket değildir; kök dizin sys.path'te olsa da "tools.make_fixture"
# implicit namespace package olarak çözülür (pytest `-m pytest` ile CWD'yi
# ekler). Betik doğrudan çalıştırıldığında da bulunabilmesi için garanti altına alınır.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.make_fixture import (  # noqa: E402 -- sys.path kurulumundan sonra
    CHANNEL_COUNT,
    START_TIME_UTC_NS,
    VALID_8RECORDS_SHA256,
    bit_status_for,
    build_valid_fixture,
    sensor_values,
    tx_status_for,
)

from sonar_analyzer.io.profile_a_format import (  # noqa: E402
    DATA_RECORD_V1,
    DATA_RECORD_V2,
    FILE_HEADER_V1,
    FILE_HEADER_V2,
)

__all__ = [
    "CHANNEL_COUNT",
    "START_TIME_UTC_NS",
    "VALID_8RECORDS_SHA256",
    "bit_status_for",
    "build_duplicate_sequence_fixture",
    "build_gap_fixture",
    "build_name_mismatch_fixture",
    "build_out_of_order_fixture",
    "build_unknown_packet_fixture",
    "build_valid_fixture",
    "build_valid_v2_fixture",
    "sensor_values",
    "tx_status_for",
]


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


def build_unknown_packet_fixture() -> bytes:
    """`F2-015`: fiziksel index 3'ün tüm 64 baytı tanınmayan çöp veriyle
    değiştirilir (yalnız adın sayısal kısmı değil, `b"Data"` öneki dahi
    yok) — `K-06`'daki (`F2-010`) sayısal `sequence_no` uyumsuzluğundan
    farklı bir bozulma sınıfı.

    Dosya yine 8 kayıt / 544 bayttır; diğer 7 kayıt sağlamdır.
    """
    buffer = bytearray(build_valid_fixture())
    record_offset = 32 + 3 * 64
    garbage = bytes((i * 7 + 13) % 256 for i in range(64))
    assert garbage[:4] != b"Data"
    buffer[record_offset : record_offset + 64] = garbage
    return bytes(buffer)


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
