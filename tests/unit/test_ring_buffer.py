"""Sabit kapasiteli canlı halka tampon — `F5-014`.

Kabul: kapasite aşılınca tanımlı eski veri çıkar; bellek sınırlı kalır.

İki bağımsız kanıt kullanılır:

1. **Bağımsız referans**: aynı yazma dizisi bir `collections.deque(maxlen=...)`
   üzerinde de yürütülüp sonuçlar karşılaştırılır. `deque(maxlen)` FIFO
   çıkarmanın kanonik tanımıdır; halka tamponun sarma aritmetiği ondan
   ayrılırsa test kalır.
2. **Ölçülen bellek**: kapasitenin 100 katı örnek yazıldıktan sonra
   `nbytes` **hiç değişmemiş** olmalı.
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.io.live.ring_buffer import ChannelRing, LiveRingBuffer


def _chunk(channel_id: str, first: int, n: int, *, quality: int | None = None) -> DataChunk:
    timestamps = np.arange(first, first + n, dtype=np.int64)
    values = timestamps.astype(np.float64) * 10.0
    flags = None if quality is None else np.full(n, quality, dtype=np.uint8)
    return DataChunk(channel_id, timestamps, values, flags)


# --------------------------------------------------------------------------- #
# kapasite altinda: hicbir sey dusmez
# --------------------------------------------------------------------------- #


def test_below_capacity_everything_is_kept() -> None:
    buffer = LiveRingBuffer(capacity_samples=100)
    evicted = buffer.append_chunk(_chunk("ch0", 0, 30))
    assert evicted == 0
    assert buffer.count("ch0") == 30

    snapshot = buffer.snapshot("ch0")
    assert snapshot.timestamps_ns.tolist() == list(range(30))
    assert snapshot.values.tolist() == [i * 10.0 for i in range(30)]


def test_exactly_at_capacity_nothing_is_evicted() -> None:
    buffer = LiveRingBuffer(capacity_samples=50)
    assert buffer.append_chunk(_chunk("ch0", 0, 50)) == 0
    assert buffer.count("ch0") == 50
    assert buffer.snapshot("ch0").timestamps_ns.tolist() == list(range(50))


def test_an_empty_chunk_is_a_no_op() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    assert buffer.append_chunk(DataChunk.empty("ch0")) == 0
    assert buffer.count("ch0") == 0


# --------------------------------------------------------------------------- #
# kapasite asilinca: EN ESKI duser (tanimli politika)
# --------------------------------------------------------------------------- #


def test_the_oldest_samples_are_evicted_first() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    buffer.append_chunk(_chunk("ch0", 0, 8))
    evicted = buffer.append_chunk(_chunk("ch0", 8, 5))  # 13 ornek, kapasite 10 -> 3 duser

    assert evicted == 3
    assert buffer.count("ch0") == 10
    assert buffer.snapshot("ch0").timestamps_ns.tolist() == list(range(3, 13))


def test_a_single_chunk_larger_than_capacity_keeps_only_the_newest_tail() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    buffer.append_chunk(_chunk("ch0", 0, 4))  # once 4 ornek koy
    evicted = buffer.append_chunk(_chunk("ch0", 100, 25))  # tek seferde kapasiteden buyuk

    assert evicted == 4 + 15  # eski 4 + yeni parcanin sigmayan 15'i
    assert buffer.count("ch0") == 10
    assert buffer.snapshot("ch0").timestamps_ns.tolist() == list(range(115, 125))


def test_evicted_total_accumulates_across_appends() -> None:
    buffer = LiveRingBuffer(capacity_samples=5)
    buffer.append_chunk(_chunk("ch0", 0, 5))
    buffer.append_chunk(_chunk("ch0", 5, 3))  # 3 duser
    buffer.append_chunk(_chunk("ch0", 8, 2))  # 2 daha duser
    assert buffer.evicted_total == 5


# --------------------------------------------------------------------------- #
# sarma (wrap) dogrulugu - bagimsiz referansla
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("capacity", [1, 2, 7, 16, 100])
@pytest.mark.parametrize("piece", [1, 3, 5, 13])
def test_matches_a_deque_reference_across_wraps(capacity: int, piece: int) -> None:
    """`deque(maxlen)` FIFO çıkarmanın kanonik tanımıdır — halka ondan ayrılmamalı."""
    buffer = LiveRingBuffer(capacity_samples=capacity)
    reference: deque[int] = deque(maxlen=capacity)

    next_value = 0
    for _ in range(20):  # kapasiteyi defalarca saracak kadar yazma turu
        buffer.append_chunk(_chunk("ch0", next_value, piece))
        reference.extend(range(next_value, next_value + piece))
        next_value += piece

    assert buffer.snapshot("ch0").timestamps_ns.tolist() == list(reference)


def test_values_and_timestamps_stay_paired_through_a_wrap() -> None:
    buffer = LiveRingBuffer(capacity_samples=6)
    for start in range(0, 20, 4):
        buffer.append_chunk(_chunk("ch0", start, 4))

    snapshot = buffer.snapshot("ch0")
    stamps = snapshot.timestamps_ns.tolist()
    values = snapshot.values.tolist()
    assert values == [float(stamp) * 10.0 for stamp in stamps]  # eslesme bozulmadi


def test_quality_flags_survive_a_wrap() -> None:
    buffer = LiveRingBuffer(capacity_samples=6)
    buffer.append_chunk(_chunk("ch0", 0, 4, quality=int(Quality.OK)))
    buffer.append_chunk(_chunk("ch0", 4, 4, quality=int(Quality.CRC_ERROR)))

    snapshot = buffer.snapshot("ch0")
    assert snapshot.quality is not None
    # Son 6 ornek: 2 tanesi OK (indeks 2,3), 4 tanesi CRC_ERROR (4..7).
    assert snapshot.quality.tolist() == [0, 0] + [int(Quality.CRC_ERROR)] * 4


# --------------------------------------------------------------------------- #
# bellek sinirli kalir (olculen)
# --------------------------------------------------------------------------- #


def test_memory_does_not_grow_with_the_stream() -> None:
    """Kapasitenin 100 katı örnek yazılsa da `nbytes` **hiç değişmez**."""
    buffer = LiveRingBuffer(capacity_samples=1000)
    buffer.append_chunk(_chunk("ch0", 0, 10))
    baseline = buffer.nbytes
    assert baseline > 0

    for start in range(0, 100_000, 500):
        buffer.append_chunk(_chunk("ch0", start, 500))

    assert buffer.nbytes == baseline
    assert buffer.count("ch0") == 1000


def test_nbytes_is_the_measured_array_footprint() -> None:
    """Elle hesaplanan bütçe: (8 + 8 + 1) bayt/örnek × kapasite."""
    ring = ChannelRing("ch0", capacity=100, with_quality=True)
    assert ring.nbytes == 100 * (8 + 8 + 1)

    without_quality = ChannelRing("ch0", capacity=100, with_quality=False)
    assert without_quality.nbytes == 100 * (8 + 8)


# --------------------------------------------------------------------------- #
# kanal yalitimi ve paket yazma
# --------------------------------------------------------------------------- #


def test_channels_have_independent_capacity() -> None:
    buffer = LiveRingBuffer(capacity_samples=5)
    buffer.append_chunk(_chunk("ch0", 0, 5))
    buffer.append_chunk(_chunk("ch1", 100, 2))

    assert buffer.count("ch0") == 5
    assert buffer.count("ch1") == 2
    assert buffer.channels() == ("ch0", "ch1")
    assert buffer.snapshot("ch1").timestamps_ns.tolist() == [100, 101]


def test_a_packet_writes_every_channel() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    packet = LivePacket(
        sequence_no=0,
        received_ns=0,
        chunks=[_chunk("ch0", 0, 3), _chunk("ch1", 50, 4)],
    )
    assert buffer.append_packet(packet) == 0
    assert buffer.count("ch0") == 3
    assert buffer.count("ch1") == 4


def test_an_unknown_channel_snapshot_is_empty_but_valid() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    snapshot = buffer.snapshot("yok")
    assert len(snapshot) == 0
    assert snapshot.channel_id == "yok"


def test_clear_empties_every_channel_and_the_counter() -> None:
    buffer = LiveRingBuffer(capacity_samples=5)
    buffer.append_chunk(_chunk("ch0", 0, 8))  # 3 duser
    assert buffer.evicted_total == 3

    buffer.clear()
    assert buffer.count("ch0") == 0
    assert buffer.evicted_total == 0
    assert len(buffer.snapshot("ch0")) == 0


# --------------------------------------------------------------------------- #
# yapilandirma dogrulamasi
# --------------------------------------------------------------------------- #


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="capacity_samples pozitif olmali"):
        LiveRingBuffer(capacity_samples=0)


def test_channel_ring_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="capacity pozitif olmali"):
        ChannelRing("ch0", capacity=0)


def test_mismatched_timestamp_and_value_lengths_are_refused() -> None:
    ring = ChannelRing("ch0", capacity=10)
    with pytest.raises(ValueError, match="uzunluklari farkli"):
        ring.append(np.zeros(3, dtype=np.int64), np.zeros(2, dtype=np.float64))
