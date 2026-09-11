"""Halka tamponun zaman penceresi sorgusu — `F5-015`.

Kabul: sarılmış buffer'da zaman sırası ve seçili aralık doğrudur.

İki zor durum ayrı ayrı kanıtlanır:

1. **Sarma**: tampon defalarca sarıldıktan sonra bile sorgu, tamponda
   gerçekten duran örneklerden **tam olarak** aralığa düşenleri, zaman
   sırasında verir (bağımsız bir Python liste referansıyla karşılaştırılır).
2. **Sıra dışı yazım**: geç gelen paketler (`F5-012`'nin `out_of_order`
   sınıfı) yazılma sırasıyla tampona girer; sorgu sonucunun sırası
   **zamana** bağlıdır, yazılma sırasına değil.
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.live.ring_buffer import LiveRingBuffer


def _chunk(channel_id: str, stamps: list[int], *, quality: int | None = None) -> DataChunk:
    timestamps = np.array(stamps, dtype=np.int64)
    values = timestamps.astype(np.float64) * 10.0
    flags = None if quality is None else np.full(len(stamps), quality, dtype=np.uint8)
    return DataChunk(channel_id, timestamps, values, flags)


def _range(start: int, end: int) -> TimeRange:
    return TimeRange(start, end)


# --------------------------------------------------------------------------- #
# temel aralik secimi
# --------------------------------------------------------------------------- #


def test_selects_exactly_the_half_open_range() -> None:
    """`[start, end)` — başlangıç dahil, bitiş hariç (`TimeRange` sözleşmesi)."""
    buffer = LiveRingBuffer(capacity_samples=100)
    buffer.append_chunk(_chunk("ch0", list(range(10))))

    result = buffer.query("ch0", _range(3, 7))
    assert result.timestamps_ns.tolist() == [3, 4, 5, 6]  # 7 dahil DEGIL


def test_a_range_covering_everything_returns_everything() -> None:
    buffer = LiveRingBuffer(capacity_samples=100)
    buffer.append_chunk(_chunk("ch0", list(range(10))))
    result = buffer.query("ch0", _range(0, 10))
    assert result.timestamps_ns.tolist() == list(range(10))


def test_a_range_outside_the_data_returns_empty_but_valid() -> None:
    buffer = LiveRingBuffer(capacity_samples=100)
    buffer.append_chunk(_chunk("ch0", list(range(10))))

    result = buffer.query("ch0", _range(1000, 2000))
    assert len(result) == 0
    assert result.channel_id == "ch0"


def test_an_unknown_channel_returns_empty_but_valid() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    result = buffer.query("yok", _range(0, 100))
    assert len(result) == 0
    assert result.channel_id == "yok"


def test_values_and_quality_follow_the_selected_timestamps() -> None:
    buffer = LiveRingBuffer(capacity_samples=100)
    buffer.append_chunk(_chunk("ch0", [10, 20, 30], quality=int(Quality.CRC_ERROR)))

    result = buffer.query("ch0", _range(20, 31))
    assert result.timestamps_ns.tolist() == [20, 30]
    assert result.values.tolist() == [200.0, 300.0]
    assert result.quality is not None
    assert result.quality.tolist() == [int(Quality.CRC_ERROR)] * 2


# --------------------------------------------------------------------------- #
# sarilmis tamponda dogruluk - bagimsiz referansla
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("capacity", [4, 9, 32])
@pytest.mark.parametrize("window", [(0, 5), (10, 25), (40, 60), (55, 1000)])
def test_a_wrapped_buffer_selects_the_same_range_as_a_plain_list_reference(
    capacity: int, window: tuple[int, int]
) -> None:
    """Referans: tamponda gerçekten duran son `capacity` örnek üzerinde elle filtre."""
    buffer = LiveRingBuffer(capacity_samples=capacity)
    written: list[int] = []
    for start in range(0, 60, 3):  # tamponu defalarca sarar
        stamps = list(range(start, start + 3))
        buffer.append_chunk(_chunk("ch0", stamps))
        written.extend(stamps)

    still_held = written[-capacity:]  # FIFO cikarma sonrasi tamponda kalanlar
    expected = [stamp for stamp in still_held if window[0] <= stamp < window[1]]

    result = buffer.query("ch0", _range(*window))
    assert result.timestamps_ns.tolist() == expected


def test_evicted_samples_are_not_returned_even_if_the_range_covers_them() -> None:
    buffer = LiveRingBuffer(capacity_samples=5)
    buffer.append_chunk(_chunk("ch0", list(range(20))))  # yalniz son 5 kalir

    result = buffer.query("ch0", _range(0, 100))
    assert result.timestamps_ns.tolist() == [15, 16, 17, 18, 19]


# --------------------------------------------------------------------------- #
# sira disi yazim: sonuc ZAMAN sirasinda olmali
# --------------------------------------------------------------------------- #


def test_out_of_order_writes_are_returned_in_time_order() -> None:
    """Geç gelen bir paket tampona sonradan yazılır ama sorguda yerine oturur."""
    buffer = LiveRingBuffer(capacity_samples=10)
    buffer.append_chunk(_chunk("ch0", [10, 20, 40]))
    buffer.append_chunk(_chunk("ch0", [30]))  # gec gelen paket

    result = buffer.query("ch0", _range(0, 100))
    assert result.timestamps_ns.tolist() == [10, 20, 30, 40]
    assert result.values.tolist() == [100.0, 200.0, 300.0, 400.0]  # deger eslesmesi bozulmadi


def test_out_of_order_writes_also_narrow_correctly() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    buffer.append_chunk(_chunk("ch0", [10, 50]))
    buffer.append_chunk(_chunk("ch0", [20, 30]))  # araya giren gec paket

    result = buffer.query("ch0", _range(15, 45))
    assert result.timestamps_ns.tolist() == [20, 30]


def test_equal_timestamps_keep_their_relative_write_order() -> None:
    """Kararlı sıralama: aynı zamanlı iki örnek yazılma sırasını korur."""
    buffer = LiveRingBuffer(capacity_samples=10)
    buffer.append_chunk(DataChunk("ch0", np.array([5], dtype=np.int64), np.array([1.0])))
    buffer.append_chunk(DataChunk("ch0", np.array([5], dtype=np.int64), np.array([2.0])))
    buffer.append_chunk(DataChunk("ch0", np.array([1], dtype=np.int64), np.array([9.0])))

    result = buffer.query("ch0", _range(0, 10))
    assert result.timestamps_ns.tolist() == [1, 5, 5]
    assert result.values.tolist() == [9.0, 1.0, 2.0]  # esitlerde yazilma sirasi korundu


# --------------------------------------------------------------------------- #
# time_span
# --------------------------------------------------------------------------- #


def test_time_span_covers_every_held_sample() -> None:
    buffer = LiveRingBuffer(capacity_samples=5)
    buffer.append_chunk(_chunk("ch0", [100, 200, 300]))

    span = buffer.time_span("ch0")
    assert span is not None
    assert span.start_ns == 100
    assert span.end_ns == 301  # yari-acik: son ornek de kapsanir
    assert buffer.query("ch0", span).timestamps_ns.tolist() == [100, 200, 300]


def test_time_span_of_an_empty_channel_is_none() -> None:
    buffer = LiveRingBuffer(capacity_samples=5)
    assert buffer.time_span("ch0") is None


def test_time_span_follows_eviction() -> None:
    buffer = LiveRingBuffer(capacity_samples=3)
    buffer.append_chunk(_chunk("ch0", [1, 2, 3, 4, 5]))  # 1 ve 2 dustu

    span = buffer.time_span("ch0")
    assert span is not None
    assert (span.start_ns, span.end_ns) == (3, 6)


def test_time_span_is_time_ordered_even_after_out_of_order_writes() -> None:
    buffer = LiveRingBuffer(capacity_samples=10)
    buffer.append_chunk(_chunk("ch0", [50, 60]))
    buffer.append_chunk(_chunk("ch0", [10]))  # gec gelen, en erken zamanli

    span = buffer.time_span("ch0")
    assert span is not None
    assert (span.start_ns, span.end_ns) == (10, 61)


# --------------------------------------------------------------------------- #
# max_points - RecordingRepository.query() ile ayni sozlesme
# --------------------------------------------------------------------------- #


def test_max_points_limits_the_result_without_losing_the_range() -> None:
    buffer = LiveRingBuffer(capacity_samples=1000)
    buffer.append_chunk(_chunk("ch0", list(range(1000))))

    result = buffer.query("ch0", _range(0, 1000), max_points=50)
    assert 0 < len(result) <= 50
    assert int(result.timestamps_ns[0]) >= 0
    assert int(result.timestamps_ns[-1]) <= 999


def test_max_points_none_returns_every_sample_in_range() -> None:
    buffer = LiveRingBuffer(capacity_samples=1000)
    buffer.append_chunk(_chunk("ch0", list(range(100))))
    assert len(buffer.query("ch0", _range(0, 100), max_points=None)) == 100
