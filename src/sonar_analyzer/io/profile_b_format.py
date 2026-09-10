"""Profil B (blok tabanlı ham akustik kayıt) alan sabitleri — `F4-009`.

Tek doğruluk kaynağı `docs/format/profile-b.md`'dir (o da `plan.md`
Bölüm 8.3'e dayanır); buradaki sabitler ve `struct.Struct` sözleşmeleri
o belgeyle **birebir** eşleşir. Herhangi bir farklılık hata sayılır ve
birlikte düzeltilir.

Bu modül yalnız **sabitleri** tanımlar. Fixture üretici `F4-010`,
payload decoder `F4-011`, blok-içi zaman `F4-012`, zaman sorgusu
bağlantısı `F4-013`.

**Profil A değişmez:** ayrı magic (`SNRBIN\x1a\x00`), ayrı dosya
yerleşimi. İki profil yalnız 125 ms kayıt ızgarasını ve `DataNNNNN`
adlandırmasını paylaşır.
"""

from __future__ import annotations

import struct

MAGIC = b"SNRBIN\x1a\x00"
END_MARKER = b"ENDR"
SUPPORTED_VERSION = 1

RECORD_PERIOD_NS = 125_000_000
RECORD_PERIOD_S = 0.125

# -- bu sürümün akustik profili (docs/format/profile-b.md §2) ---------------

#: 48 kHz hidrofon; Profil B taslağının (96 kHz) yarısı.
ACOUSTIC_SAMPLE_RATE_HZ = 48_000
#: 125 ms penceredeki örnek sayısı = 48000 * 0.125.
SAMPLES_PER_BLOCK = 6_000
#: SENSOR_RAW akustik payload dtype kodu (`int16`).
ACOUSTIC_DTYPE_CODE = 0x01
ACOUSTIC_DTYPE_SIZE = 2
ACOUSTIC_NUMPY_DTYPE = "<i2"
#: BlockHeader.block_size (yalnız payload) = 6000 * 2.
ACOUSTIC_PAYLOAD_BYTES = SAMPLES_PER_BLOCK * ACOUSTIC_DTYPE_SIZE
#: Bu profilde tanımlı akustik kanal kimlikleri (Hydrophone 1..4).
ACOUSTIC_CHANNEL_IDS: tuple[int, ...] = (0, 1, 2, 3)
#: docs/format/profile-b.md §2.1 — kanal başına yol / kısa ad / birim.
ACOUSTIC_CHANNELS: tuple[tuple[int, str, str, str], ...] = (
    (0, "Acoustic/Hydrophone 1", "Hydrophone 1", "Pa"),
    (1, "Acoustic/Hydrophone 2", "Hydrophone 2", "Pa"),
    (2, "Acoustic/Hydrophone 3", "Hydrophone 3", "Pa"),
    (3, "Acoustic/Hydrophone 4", "Hydrophone 4", "Pa"),
)

# -- blok türleri ve dtype kodları (plan.md §8.3.5) ------------------------

BLOCK_TYPE_SENSOR_RAW = 0x0001
BLOCK_TYPE_SENSOR_SCALED = 0x0002
BLOCK_TYPE_NAV_IMU = 0x0010
BLOCK_TYPE_TX_STATUS = 0x0020
BLOCK_TYPE_BIT_STATUS = 0x0030
BLOCK_TYPE_EVENT_LOG = 0x0040
BLOCK_TYPE_PAD = 0x00F0

DTYPE_SIZE: dict[int, int] = {0x01: 2, 0x02: 4, 0x03: 4, 0x04: 8, 0x05: 1}
NUMPY_DTYPE: dict[int, str] = {
    0x01: "<i2",
    0x02: "<i4",
    0x03: "<f4",
    0x04: "<f8",
    0x05: "u1",
}

# -- struct sözleşmeleri (docs/format/profile-b.md §3, plan.md §8.3.11) ----

FILE_HEADER = struct.Struct("<8sHHHHIIIQ16sI196sI")  # 256 B
CHANNEL_ENTRY = struct.Struct("<HBB24s8sfffHH12s")  # 64 B
RECORD_HEADER = struct.Struct("<12sIIHHqQII")  # 48 B
BLOCK_HEADER = struct.Struct("<HHIHBBi")  # 16 B
RECORD_TRAILER = struct.Struct("<I4s")  # 8 B
INDEX_ENTRY = struct.Struct("<IQqII4s")  # 32 B

FILE_HEADER_SIZE = 256
CHANNEL_ENTRY_SIZE = 64
RECORD_HEADER_SIZE = 48
BLOCK_HEADER_SIZE = 16
RECORD_TRAILER_SIZE = 8

assert FILE_HEADER.size == FILE_HEADER_SIZE
assert CHANNEL_ENTRY.size == CHANNEL_ENTRY_SIZE
assert RECORD_HEADER.size == RECORD_HEADER_SIZE
assert BLOCK_HEADER.size == BLOCK_HEADER_SIZE
assert RECORD_TRAILER.size == RECORD_TRAILER_SIZE


def align8(n: int) -> int:
    """Bir bloğun kapladığı alan 8 bayta hizalanır (artan baytlar sıfır)."""
    return (n + 7) & ~7


def acoustic_block_stride() -> int:
    """Bir SENSOR_RAW akustik bloğunun kayıttaki toplam alanı (başlık + payload + pad)."""
    return align8(BLOCK_HEADER_SIZE + ACOUSTIC_PAYLOAD_BYTES)


def record_name(record_index: int, prefix: str = "Data", digits: int = 5) -> str:
    """`Data00000`, `Data00001`, … (Profil A ile aynı kural)."""
    return f"{prefix}{record_index % 10**digits:0{digits}d}"
