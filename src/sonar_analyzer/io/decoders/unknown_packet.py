"""Bilinmeyen paket teşhisi — `F2-015`.

Plan Bölüm 8.4: "Bilinmeyen paketleri atmak yerine konum ve tür bilgisiyle
raporla." ve "Hatalı kayıtların kalan dosyanın okunmasını mümkün olduğunca
engellememesini sağla."

Profil A kayıtları sabit boyutludur; `record_size` header'dan **güvenilir**
şekilde bilinir (`F2-004`'te doğrulanır). Bu yüzden bir kaydın `name`
alanı beklenen `b"Data"` önekiyle başlamıyorsa bile — K-06'daki (`F2-010`)
sayısal `sequence_no` uyumsuzluğundan farklı olarak, alan tümüyle
tanınmayan bir bayt dizisiyse — tarama durmaz: `record_size` kadar ileri
atlanır, kayıt `UnknownPacket` olarak raporlanır.

Güvenilir bir uzunluk yoksa (`record_size`'ın kendisi şüpheliyse, örn. ağır
bozulma sonrası resync gerekiyorsa) ileri atlanamaz; `scan_for_resync_point`
sonraki hizalı `b"Data"` desenini arar. Bulunamazsa yalnız konum raporlanır
(plan Bölüm 8.3.12 resync stratejisiyle aynı ilke).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from sonar_analyzer.io.decoders.profile_a import decode_record_at_index, record_count_in_buffer
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_RECORD_SIZE_V1,
    DataRecordV1,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer

#: docs/format/timing-and-naming.md §2 — her kayıt adı bu önekle başlar.
_EXPECTED_NAME_PREFIX = b"Data"


@dataclass(frozen=True)
class UnknownPacket:
    """`name` alanı tanınmayan bir kayıt; atılmaz, teşhis olarak raporlanır."""

    byte_offset: int
    reason: str
    #: Güvenilir uzunluk biliniyorsa atlanan bayt sayısı; yoksa `None`
    #: (yalnız konum raporlanabildi, tarama ilerletilemedi).
    skipped_bytes: int | None

    def __str__(self) -> str:
        if self.skipped_bytes is None:
            return (
                f"Bilinmeyen paket: offset {self.byte_offset}, {self.reason} "
                "(guvenilir uzunluk yok)"
            )
        return (
            f"Bilinmeyen paket: offset {self.byte_offset}, {self.reason}, "
            f"{self.skipped_bytes} bayt atlanip devam edildi"
        )


def classify_record_bytes(
    raw_record: bytes, byte_offset: int, record_size: int
) -> UnknownPacket | None:
    """Kaydın `name` alanı `b"Data"` ile başlamıyorsa `UnknownPacket` döner.

    `record_size` header'dan bilindiği (güvenilir uzunluk) için, dönen
    `UnknownPacket.skipped_bytes == record_size` olur: çağıran taraf bu
    kadar ileri atlayıp taramaya devam edebilir, okuma durmaz.
    """
    name_prefix = raw_record[:4]
    if name_prefix == _EXPECTED_NAME_PREFIX:
        return None
    return UnknownPacket(
        byte_offset=byte_offset,
        reason=f"beklenmeyen onek {name_prefix!r}",
        skipped_bytes=record_size,
    )


def scan_for_resync_point(
    buffer: ReadableBuffer,
    start_offset: int,
    search_limit: int | None = None,
    alignment: int = 8,
) -> int | None:
    """Güvenilir uzunluk yokken, sonraki hizalı `b"Data"` konumunu arar.

    `start_offset`'ten itibaren `alignment` bayt adımlarla tarar. Bulunursa
    o offset döner (bundan sonra uzunluk yeniden güvenilir sayılabilir);
    `search_limit` bayt içinde (veya buffer sonuna kadar) bulunamazsa
    `None` döner — bu durumda yalnızca konum raporlanabilir, tarama
    ilerletilemez (kabul kriterinin ikinci dalı).
    """
    end = len(buffer) if search_limit is None else min(len(buffer), start_offset + search_limit)
    offset = start_offset
    while offset + len(_EXPECTED_NAME_PREFIX) <= end:
        if bytes(buffer[offset : offset + 4]) == _EXPECTED_NAME_PREFIX:
            return offset
        offset += alignment
    return None


def iter_records_with_unknown_packets(
    buffer: ReadableBuffer,
    header_size: int = EXPECTED_HEADER_SIZE_V1,
    record_size: int = EXPECTED_RECORD_SIZE_V1,
) -> Iterator[DataRecordV1 | UnknownPacket]:
    """`iter_records` gibi tarar ama tanınmayan kayıtları atmak yerine raporlar.

    `record_size` her zaman güvenilir kabul edilir (Profil A sabit boyutlu
    kayıt tasarımı); bu yüzden bilinmeyen bir kayıtla karşılaşınca okuma
    durmaz, `record_size` kadar ileri atlanıp devam edilir — sağlam
    kayıtların okunması engellenmez.
    """
    count = record_count_in_buffer(len(buffer), header_size, record_size)
    for index in range(count):
        offset = header_size + index * record_size
        raw_record = bytes(buffer[offset : offset + record_size])
        unknown = classify_record_bytes(raw_record, offset, record_size)
        if unknown is not None:
            yield unknown
            continue
        yield decode_record_at_index(buffer, index, header_size, record_size)
