"""Profil A alan sabitleri ve veri modeli — `F2-001`.

Tek doğruluk kaynağı `docs/format/profile-a.md`'dir; buradaki sabitler ve
`struct.Struct` sözleşmeleri o belgeyle **birebir** eşleşir. Herhangi bir
farklılık hata sayılır ve ikisi birlikte düzeltilir.

Bu modül yalnız **sabitleri ve veri modelini** tanımlar; okuma/doğrulama
mantığı `io/readers/` ve `io/decoders/` katmanlarındadır (plan Bölüm 7.1
katman ayrımı: `io` GUI'yi bilmez, burada zaten hiçbiri yok).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# -- surum 1: CRC'siz (docs/format/profile-a.md) ----------------------------

MAGIC = b"SONARBIN"
SUPPORTED_VERSIONS: frozenset[int] = frozenset({1, 2})

EXPECTED_HEADER_SIZE_V1 = 32
EXPECTED_RECORD_SIZE_V1 = 64
EXPECTED_PERIOD_US = 125_000
EXPECTED_CHANNEL_COUNT = 8

#: docs/format/profile-a.md §2.1 — 32 bayt.
FILE_HEADER_V1 = struct.Struct("<8sHHIIIQ")
assert FILE_HEADER_V1.size == EXPECTED_HEADER_SIZE_V1

#: docs/format/profile-a.md §5.1 — 64 bayt (8 kanallı ontanimli).
DATA_RECORD_V1 = struct.Struct("<12sIQ8fII")
assert DATA_RECORD_V1.size == EXPECTED_RECORD_SIZE_V1

# -- surum 2: CRC destekli (docs/adr/ADR-011-crc.md §2.3) --------------------

EXPECTED_HEADER_SIZE_V2 = 36
EXPECTED_RECORD_SIZE_V2 = 68

#: ADR-011 §2.3 — 36 bayt (v1 govdesi + header_crc32).
FILE_HEADER_V2 = struct.Struct("<8sHHIIIQI")
assert FILE_HEADER_V2.size == EXPECTED_HEADER_SIZE_V2

#: ADR-011 §2.3 — 68 bayt (v1 kayit govdesi + crc32).
DATA_RECORD_V2 = struct.Struct("<12sIQ8fII I")
assert DATA_RECORD_V2.size == EXPECTED_RECORD_SIZE_V2

#: docs/format/timing-and-naming.md §1.
RECORD_PERIOD_NS = 125_000_000

#: docs/format/channel-map.md §4.1 — BIT bit haritasi (bit_status alani).
BIT_COMPONENT_BY_BIT: dict[int, str] = {
    0: "Power Supply",
    1: "Power Supply",
    2: "Power Supply",
    3: "Power Supply",
    4: "Communication",
    5: "Communication",
    6: "Communication",
    7: "Communication",
    8: "Thermal Management",
    9: "Thermal Management",
    10: "Thermal Management",
    11: "Thermal Management",
}

#: docs/format/profile-a.md §5.2 — tx_status kod eslemesi.
TX_STATE_LABELS: dict[int, str] = {0: "IDLE", 1: "ACTIVE", 2: "FAULT"}


@dataclass(frozen=True)
class FileHeaderV1:
    """32 baytlık dosya başlığının çözülmüş hâli (CRC'siz)."""

    magic: bytes
    version: int
    header_size: int
    record_size: int
    period_us: int
    channel_count: int
    start_time_utc_ns: int


@dataclass(frozen=True)
class FileHeaderV2:
    """36 baytlık dosya başlığının çözülmüş hâli (CRC destekli)."""

    magic: bytes
    version: int
    header_size: int
    record_size: int
    period_us: int
    channel_count: int
    start_time_utc_ns: int
    header_crc32: int


@dataclass(frozen=True)
class DataRecordV1:
    """64 baytlık `DataNNNNN` kaydının çözülmüş hâli (8 sabit kanal)."""

    name: bytes
    sequence_no: int
    elapsed_us: int
    sensor_values: tuple[float, float, float, float, float, float, float, float]
    bit_status: int
    tx_status: int


def record_name(sequence_no: int, digits: int = 5) -> str:
    """`docs/format/timing-and-naming.md` §2: ad sarmaz, en az `digits` hane."""
    return f"Data{sequence_no:0{digits}d}"
