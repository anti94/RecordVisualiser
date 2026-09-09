"""Cihaz tick dönüşüm adaptörü — `F2-025`.

Kabul: referans tick değerleri doğru ns üretir; ham tick saklanır.
`docs/adr/ADR-003-time-base.md` §2.3'ün doğrulama noktalarından biri.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.time_base import TimeBase, ticks_to_utc_ns
from sonar_analyzer.io.decoders.tick_conversion import (
    TickConversionResult,
    convert_tick,
    convert_ticks_batch,
)

#: 10 MHz sayaç, epoch 2026-09-08T21:00:00Z (golden_bytes.START_TIME_UTC_NS ile ayni).
_TB_10MHZ = TimeBase(id="device0", epoch_utc_ns=1_788_901_200_000_000_000, tick_hz=10_000_000)

#: 1 kHz sayaç, epoch 0 -- tam bolunen basit referans degerler icin.
_TB_1KHZ = TimeBase(id="device0", epoch_utc_ns=0, tick_hz=1_000)


# -- referans tick -> dogru ns -----------------------------------------


def test_known_tick_value_produces_expected_ns_at_1khz() -> None:
    """Kabul kriteri: bilinen referans tick degerleri dogru ns uretir.

    1 kHz'de 1 tick = 1 ms = 1_000_000 ns. 500 tick -> 500_000_000 ns.
    """
    assert ticks_to_utc_ns(_TB_1KHZ, ticks=500, ticks0=0) == 500_000_000


def test_zero_ticks_since_epoch_returns_epoch_itself() -> None:
    assert ticks_to_utc_ns(_TB_1KHZ, ticks=0, ticks0=0) == 0
    assert ticks_to_utc_ns(_TB_10MHZ, ticks=42, ticks0=42) == _TB_10MHZ.epoch_utc_ns


def test_known_tick_value_produces_expected_ns_at_10mhz() -> None:
    """10 MHz'de 1 saniye = 10_000_000 tick."""
    result = ticks_to_utc_ns(_TB_10MHZ, ticks=10_000_000, ticks0=0)
    assert result == _TB_10MHZ.epoch_utc_ns + 1_000_000_000


def test_nonzero_ticks0_is_used_as_reference_point() -> None:
    """ticks0, epoch_utc_ns'in karsilik geldigi tick degeridir."""
    # ticks0=1000 -> epoch bu noktada; 1500 tick sonra 500 tick fark = 500ms (1kHz).
    result = ticks_to_utc_ns(_TB_1KHZ, ticks=1500, ticks0=1000)
    assert result == 500_000_000


def test_ticks_before_ticks0_produce_negative_offset() -> None:
    result = ticks_to_utc_ns(_TB_1KHZ, ticks=0, ticks0=500)
    assert result == -500_000_000


def test_tick_hz_zero_raises_because_no_counter_exists() -> None:
    """ADR-003 §2.3: Profil A icin tick_hz=0 -- bu fonksiyon cagrilmamali."""
    tb = TimeBase(id="none", epoch_utc_ns=0, tick_hz=0)
    with pytest.raises(ValueError, match="tick_hz=0"):
        ticks_to_utc_ns(tb, ticks=1, ticks0=0)


def test_time_base_has_counter_reflects_tick_hz() -> None:
    assert TimeBase(id="a", epoch_utc_ns=0, tick_hz=0).has_counter is False
    assert TimeBase(id="a", epoch_utc_ns=0, tick_hz=1000).has_counter is True


def test_time_base_rejects_negative_tick_hz() -> None:
    with pytest.raises(ValueError, match="negatif"):
        TimeBase(id="a", epoch_utc_ns=0, tick_hz=-1)


def test_time_base_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="id bos olamaz"):
        TimeBase(id="  ", epoch_utc_ns=0, tick_hz=1000)


# -- ham tick saklanir (kabul kriterinin ikinci yarisi) ----------------


def test_convert_tick_preserves_raw_ticks_value() -> None:
    """Kabul kriteri: ham tick saklanir."""
    result = convert_tick(_TB_1KHZ, ticks=500, ticks0=0)

    assert isinstance(result, TickConversionResult)
    assert result.raw_ticks == 500
    assert result.timestamp_utc_ns == 500_000_000
    assert result.time_base_id == "device0"


def test_convert_tick_preserves_raw_ticks_even_for_large_10mhz_values() -> None:
    result = convert_tick(_TB_10MHZ, ticks=123_456_789, ticks0=0)
    assert result.raw_ticks == 123_456_789


def test_convert_ticks_batch_preserves_each_raw_value_in_order() -> None:
    ticks_sequence = [0, 250, 500, 750, 1000]
    results = convert_ticks_batch(_TB_1KHZ, ticks_sequence, ticks0=0)

    assert [r.raw_ticks for r in results] == ticks_sequence
    assert [r.timestamp_utc_ns for r in results] == [
        0,
        250_000_000,
        500_000_000,
        750_000_000,
        1_000_000_000,
    ]


def test_tick_conversion_result_is_immutable() -> None:
    import dataclasses

    result = TickConversionResult(raw_ticks=1, timestamp_utc_ns=1, time_base_id="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.raw_ticks = 2  # type: ignore[misc]
