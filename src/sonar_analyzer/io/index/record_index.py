"""Kayıt offseti ve zaman indeksini oluşturma — `F2-028`.

Plan Bölüm 8.5: dosya açılışında minimum taramayla üretilir. Her fiziksel
kaydın offseti ve zamanı sıralı bir indekste saklanır; bu, kayıt sayısı
büyüdükçe zaman-aralığı sorgularının tam taramaya değil indeks üzerinden
ikili aramaya dayanmasını sağlar (`F2-034`).

Sıra **fiziksel sıradır** (dosyadaki yazım sırası) — `sequence_no` tekrarlı
veya sırasız olabilir (`F2-011`); indeks bunu gizlemez, olduğu gibi taşır.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.io.decoders.profile_a import iter_records
from sonar_analyzer.io.decoders.timing import record_timestamp_ns
from sonar_analyzer.io.profile_a_format import FileHeaderV1
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer


@dataclass(frozen=True)
class RecordIndexEntry:
    """Tek bir kaydın fiziksel konumu ve zamanı."""

    sequence_no: int
    byte_offset: int
    timestamp_ns: int


def build_record_index(buffer: ReadableBuffer, header: FileHeaderV1) -> list[RecordIndexEntry]:
    """Buffer'daki tüm tam kayıtlar için `RecordIndexEntry` listesi üretir.

    Her girdinin `byte_offset`'i **tam** bir kayıt sınırıdır — her zaman
    `header.header_size + n * header.record_size` formülüyle üretilir,
    kayıt gövdesinin ortasına asla işaret etmez (kabul kriteri). Kesik son
    kayıt (`F2-009`) indekse hiç girmez; `iter_records` zaten yalnız tam
    kayıtları döner.
    """
    entries: list[RecordIndexEntry] = []
    offset = header.header_size
    for record in iter_records(buffer, header.header_size, header.record_size):
        entries.append(
            RecordIndexEntry(
                sequence_no=record.sequence_no,
                byte_offset=offset,
                timestamp_ns=record_timestamp_ns(header, record),
            )
        )
        offset += header.record_size
    return entries
