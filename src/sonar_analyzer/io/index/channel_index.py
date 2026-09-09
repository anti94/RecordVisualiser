"""Kanal indeksini oluşturma — `F2-029`.

Profil A **yoğun** (dense) bir formattır: her kayıt tüm kanalların değerini
taşır, hiçbir kanal seyrek değildir (`docs/format/channel-map.md`). Bu
yüzden kanal indeksi, her kanal için örnek sayısını ve kapsanan zaman
aralığını (`F2-028`'in kayıt indeksinden) saklar — rastgele erişimde tüm
kayıtları yeniden taramaya gerek kalmaz.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sonar_analyzer.io.index.record_index import RecordIndexEntry


@dataclass(frozen=True)
class ChannelIndexEntry:
    """Bir kanalın indeksteki özeti."""

    channel_id: str
    sample_count: int
    first_timestamp_ns: int | None
    last_timestamp_ns: int | None


def build_channel_index(
    record_entries: Sequence[RecordIndexEntry],
    channel_ids: Sequence[str],
) -> dict[str, ChannelIndexEntry]:
    """Her kanal için örnek sayısı ve zaman aralığını hesaplar.

    Profil A'da her kayıt tüm kanalları taşıdığı için `sample_count` her
    kanalda aynıdır ve `len(record_entries)`'e eşittir (kabul kriterinin
    "kanal sorgusu referans sayıları verir" kısmı). Zaman aralığı
    `min`/`max` ile hesaplanır — fiziksel sıra sırasız olsa bile
    (`F2-011`) kapsanan aralık doğru kalır.
    """
    if not record_entries:
        return {
            channel_id: ChannelIndexEntry(channel_id, 0, None, None) for channel_id in channel_ids
        }

    timestamps = [entry.timestamp_ns for entry in record_entries]
    first_timestamp_ns = min(timestamps)
    last_timestamp_ns = max(timestamps)
    count = len(record_entries)

    return {
        channel_id: ChannelIndexEntry(channel_id, count, first_timestamp_ns, last_timestamp_ns)
        for channel_id in channel_ids
    }
