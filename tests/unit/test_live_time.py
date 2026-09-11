"""Canlı cihaz zamanını kanonik zamana bağlama — `F5-013`.

Kabul: dosya ve canlı replay aynı zaman tabanında eşleşir.

Bu iddia mimari olarak sağlanıyor: dosya tarafı (`F2-025`'in
`tick_conversion.convert_tick`) ve canlı tarafı (`live_time.
canonical_window_start_ns`) **aynı** `domain.time_base.ticks_to_utc_ns()`
çekirdeğini çağırıyor. Testler bunu iki düzeyde kanıtlıyor: aynı
`(time_base, ticks, ticks0)` üçlüsü için ikisinin bit düzeyinde aynı
sonucu verdiğini, ve `TimedWindow`'un cihaz-sayacı kaynaklı zamanla
payload'ın kendi zamanı arasındaki gerçek bir anlaşmazlığı doğru tespit
ettiğini.
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_base import TimeBase
from sonar_analyzer.io.decoders.tick_conversion import convert_tick
from sonar_analyzer.io.live.live_time import (
    JITTER_TOLERANCE_NS,
    TimedWindow,
    canonical_window_start_ns,
    timed_window,
    timed_window_from_packet,
)
from sonar_analyzer.io.live.wire_header import PROTOCOL_UDP, LiveWireHeader

_TIME_BASE = TimeBase(
    id="device0", epoch_utc_ns=1_788_901_200_000_000_000, tick_hz=48_000, source="local_oscillator"
)


def _header(device_ticks: int) -> LiveWireHeader:
    return LiveWireHeader(
        PROTOCOL_UDP,
        flags=0,
        sequence_no=0,
        fragment_index=0,
        fragment_count=1,
        device_ticks=device_ticks,
        payload_length=0,
    )


def _chunk(channel_id: str, first_ns: int, n: int = 3) -> DataChunk:
    timestamps = first_ns + np.arange(n, dtype=np.int64) * 1_000_000
    values = np.zeros(n, dtype=np.float64)
    return DataChunk(channel_id, timestamps, values)


# --------------------------------------------------------------------------- #
# dosya ve canli AYNI cekirdegi kullanir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("device_ticks", [0, 1, 6000, 48_000, 1_000_000, 2**31, 2**32 - 1, 2**40])
def test_live_and_file_side_produce_bit_identical_canonical_time(device_ticks: int) -> None:
    """Aynı `(time_base, ticks, ticks0)` — dosya (`F2-025`) ve canlı aynı sonucu verir."""
    ticks0 = 0
    file_side = convert_tick(_TIME_BASE, device_ticks, ticks0).timestamp_utc_ns
    live_side = canonical_window_start_ns(_header(device_ticks), _TIME_BASE, ticks0)
    assert live_side == file_side


def test_live_and_file_side_agree_with_a_nonzero_ticks0_anchor() -> None:
    ticks0 = 1000
    device_ticks = 1000 + 48_000  # ticks0'dan 1 saniye sonra
    file_side = convert_tick(_TIME_BASE, device_ticks, ticks0).timestamp_utc_ns
    live_side = canonical_window_start_ns(_header(device_ticks), _TIME_BASE, ticks0)
    assert live_side == file_side
    assert live_side == _TIME_BASE.epoch_utc_ns + 1_000_000_000  # tam 1 saniye sonra


# --------------------------------------------------------------------------- #
# TimedWindow - anlasma/anlasmazlik
# --------------------------------------------------------------------------- #


def test_a_window_with_no_payload_data_trivially_agrees() -> None:
    window = TimedWindow(canonical_window_start_ns=123, payload_first_sample_ns=None)
    assert window.agrees_with_payload is True
    assert window.deviation_ns is None


def test_an_exact_match_agrees() -> None:
    window = TimedWindow(canonical_window_start_ns=1000, payload_first_sample_ns=1000)
    assert window.agrees_with_payload is True
    assert window.deviation_ns == 0


def test_a_deviation_within_tolerance_agrees() -> None:
    window = TimedWindow(
        canonical_window_start_ns=1_000_000_000,
        payload_first_sample_ns=1_000_000_000 + JITTER_TOLERANCE_NS,
    )
    assert window.agrees_with_payload is True


def test_a_deviation_beyond_tolerance_disagrees() -> None:
    window = TimedWindow(
        canonical_window_start_ns=1_000_000_000,
        payload_first_sample_ns=1_000_000_000 + JITTER_TOLERANCE_NS + 1,
    )
    assert window.agrees_with_payload is False
    assert window.deviation_ns == -(JITTER_TOLERANCE_NS + 1)


def test_a_real_clock_drift_scenario_is_caught() -> None:
    """Cihaz sayacı 10 ms ileri kaymış bir payloadla eşleşmeli — bu gerçek bir anomali."""
    device_ticks = 480_000  # 10 saniye (48 kHz)
    header = _header(device_ticks)
    canonical = canonical_window_start_ns(header, _TIME_BASE, ticks0=0)
    drifted_payload_ns = canonical + 10_000_000  # payload 10 ms ileriden geliyor

    window = timed_window(header, _TIME_BASE, 0, drifted_payload_ns)
    assert window.agrees_with_payload is False
    assert window.deviation_ns == -10_000_000


# --------------------------------------------------------------------------- #
# timed_window_from_packet - chunks'tan cikarim
# --------------------------------------------------------------------------- #


def test_extracts_the_earliest_sample_across_multiple_channels() -> None:
    header = _header(device_ticks=0)
    canonical = canonical_window_start_ns(header, _TIME_BASE, 0)
    chunks = [
        _chunk("ch0", canonical + 5_000_000),  # gec baslayan kanal
        _chunk("ch1", canonical),  # tam kanonikte baslayan kanal
    ]
    window = timed_window_from_packet(header, chunks, _TIME_BASE, 0)
    assert window.payload_first_sample_ns == canonical  # en erken olan secildi
    assert window.agrees_with_payload is True


def test_empty_chunks_have_no_payload_reference_time() -> None:
    header = _header(device_ticks=0)
    window = timed_window_from_packet(header, [], _TIME_BASE, 0)
    assert window.payload_first_sample_ns is None
    assert window.agrees_with_payload is True  # karsilastirilacak bir sey yok


def test_a_channel_with_zero_samples_is_ignored() -> None:
    header = _header(device_ticks=0)
    canonical = canonical_window_start_ns(header, _TIME_BASE, 0)
    empty = DataChunk("ch0", np.array([], dtype=np.int64), np.array([], dtype=np.float64))
    real = _chunk("ch1", canonical)
    window = timed_window_from_packet(header, [empty, real], _TIME_BASE, 0)
    assert window.payload_first_sample_ns == canonical
