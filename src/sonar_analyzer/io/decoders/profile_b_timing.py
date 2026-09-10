"""Profil B blok içi örnek zamanları — `F4-012`.

Profil B'de mutlak zaman yalnız `FileHeader.t0_utc_ns`'de bulunur;
kayıtlar 125 ms ızgarasına göre offset taşır. Bir `SENSOR_RAW` bloğu
o 125 ms pencerenin `sample_count` örneğini taşır. Bu modül her örneğe
**kanonik `int64` ns** zaman damgası üretir (ADR-003).

İki değişmez:

1. **Pencereyi kapsar.** Bir bloğun 6000 örneği `[blok_baslangici,
   blok_baslangici + 125 ms)` yarı-açık aralığındadır; `i`. örnek
   `blok_baslangici + i * 1e9 // sample_rate_hz` (tam sayı bölme —
   toplam sapma birikmez, `6000 * 1e9 // 48000 = 125_000_000` tam).
2. **Blok sınırında tekrar yok.** Bir bloğun son örnek zamanı, sonraki
   bloğun ilk örnek zamanından **kesinlikle küçüktür** (aradaki boşluk
   yaklaşık bir örnek periyodudur, tekrar değil).

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.io.decoders.profile_b import (
    DecodedRecord,
    decode_file_header,
    iter_records,
)
from sonar_analyzer.io.profile_b_format import ACOUSTIC_SAMPLE_RATE_HZ
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer

NS_PER_SECOND = 1_000_000_000


def block_sample_times_ns(
    block_start_ns: int,
    sample_count: int,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> NDArray[np.int64]:
    """`block_start_ns`'ten başlayan `sample_count` örneğin ns damgaları.

    `i`. örnek = `block_start_ns + i * 1e9 // sample_rate_hz`. Tam sayı
    bölme kullanılır; böylece `sample_count = 6000`, `sample_rate = 48000`
    için son eleman + bir adım tam olarak 125 ms'ye denk gelir ve
    kayan-nokta birikimi olmaz.
    """
    if sample_count < 0:
        raise ValueError(f"sample_count negatif olamaz: {sample_count}")
    if sample_rate_hz <= 0:
        raise ValueError(f"sample_rate_hz pozitif olmalı: {sample_rate_hz}")
    indices = np.arange(sample_count, dtype=np.int64)
    return block_start_ns + (indices * NS_PER_SECOND) // sample_rate_hz


def block_span_ns(sample_count: int, sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ) -> int:
    """Bir bloğun kapsadığı süre (ns): `sample_count * 1e9 // sample_rate_hz`.

    48 kHz / 6000 örnek için tam `125_000_000` (125 ms).
    """
    return (sample_count * NS_PER_SECOND) // sample_rate_hz


def record_block_sample_times_ns(
    record: DecodedRecord,
    channel_id: int,
    t0_utc_ns: int = 0,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> NDArray[np.int64]:
    """Bir kaydın `channel_id` `SENSOR_RAW` bloğunun örnek zamanları.

    Blok başlangıcı = `t0_utc_ns + record.t_start_offset_ns + block.t_offset_ns`.
    """
    block = record.sensor_block(channel_id)
    if block is None or block.samples is None:
        return np.empty(0, dtype=np.int64)
    block_start = t0_utc_ns + record.t_start_offset_ns + block.t_offset_ns
    return block_sample_times_ns(block_start, block.samples.shape[0], sample_rate_hz)


def channel_sample_times_ns(
    buffer: ReadableBuffer,
    channel_id: int,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> NDArray[np.int64]:
    """Bir kanalın **tüm** kayıtlardaki örnek zamanları, kesintisiz artan.

    `FileHeader.t0_utc_ns` ankor alınır. Sonuç kesinlikle monoton artar
    (blok sınırında tekrar yok) ve `record_count * span` süresini
    kapsar.
    """

    t0 = decode_file_header(buffer).t0_utc_ns
    parts: list[NDArray[np.int64]] = []
    for record in iter_records(buffer):
        times = record_block_sample_times_ns(record, channel_id, t0, sample_rate_hz)
        if times.size:
            parts.append(times)
    if not parts:
        return np.empty(0, dtype=np.int64)
    return np.concatenate(parts)
