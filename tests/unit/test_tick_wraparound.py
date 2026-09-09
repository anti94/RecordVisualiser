"""Sayaç sarması (wraparound) ve saat resetini ayırt etme — `F2-026`.

Kabul: iki sentetik senaryo farklı teşhis ve zaman kalitesi üretir.
`docs/adr/ADR-003-time-base.md` §2.4/§2.5'in doğrulama noktalarından biri:
"uint32 sarma unwrap, reset tespiti" (`tests/unit/test_time_base.py`
referansı, §5 Doğrulama).
"""

from __future__ import annotations

from sonar_analyzer.io.decoders.tick_wraparound import (
    SyncQuality,
    TickAnomaly,
    TickAnomalyKind,
    detect_tick_anomaly,
    sync_quality_for_anomaly,
)

#: uint32 sayaç, 10 MHz — ADR-003 tablosu: sarma ~429 s (~7 dk).
COUNTER_BITS = 32
COUNTER_RANGE = 1 << COUNTER_BITS
TICK_HZ = 10_000_000
NOMINAL_PERIOD_TICKS = int(0.125 * TICK_HZ)  # 125 ms kayit periyodu -> 1_250_000 tick
#: ADR-003 §2.4: "nominal periyodun birkac kati" -- 5x tolerans.
MAX_PLAUSIBLE_DELTA = 5 * NOMINAL_PERIOD_TICKS


# -- senaryo 1: sarma (wraparound) ------------------------------------------


def test_scenario_1_wraparound_is_classified_as_wraparound() -> None:
    """Sentetik senaryo 1: sayaç uint32 sınırına yakınken normal ilerleyip sarıyor."""
    previous_ticks = COUNTER_RANGE - 96  # 4294967200
    observed_ticks = 50  # sarma sonrasi kucuk deger

    anomaly = detect_tick_anomaly(
        previous_ticks, observed_ticks, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=10
    )

    assert anomaly is not None
    assert anomaly.kind is TickAnomalyKind.WRAPAROUND
    assert anomaly.previous_ticks == previous_ticks
    assert anomaly.observed_ticks == observed_ticks
    # delta = (50 + 2**32) - (2**32 - 96) = 146; unwrap = previous + 146.
    assert anomaly.unwrapped_ticks == previous_ticks + 146


def test_scenario_1_wraparound_has_good_sync_quality() -> None:
    anomaly = detect_tick_anomaly(
        COUNTER_RANGE - 96, 50, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=10
    )
    assert sync_quality_for_anomaly(anomaly) == SyncQuality.GOOD


# -- senaryo 2: reset -----------------------------------------------------


def test_scenario_2_unexplained_regression_is_classified_as_reset() -> None:
    """Sentetik senaryo 2: kayit ortasinda, sayac sinirindan uzakken deger kuculuyor."""
    previous_ticks = 5_000_000  # sinirdan cok uzak, orta-kayit
    observed_ticks = 100  # aciklanamayan kucuk deger

    anomaly = detect_tick_anomaly(
        previous_ticks, observed_ticks, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=20
    )

    assert anomaly is not None
    assert anomaly.kind is TickAnomalyKind.RESET
    assert anomaly.unwrapped_ticks is None


def test_scenario_2_reset_has_suspect_sync_quality() -> None:
    anomaly = detect_tick_anomaly(5_000_000, 100, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=20)
    assert sync_quality_for_anomaly(anomaly) == SyncQuality.SUSPECT


# -- kabul kriterinin ozu: iki senaryo birbirinden farkli -------------------


def test_wraparound_and_reset_produce_different_diagnosis_and_quality() -> None:
    """Kabul kriteri birebir: iki sentetik senaryo farkli teshis ve zaman kalitesi uretir."""
    wraparound = detect_tick_anomaly(
        COUNTER_RANGE - 96, 50, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=10
    )
    reset = detect_tick_anomaly(5_000_000, 100, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=20)

    assert wraparound is not None
    assert reset is not None
    assert wraparound.kind != reset.kind
    assert sync_quality_for_anomaly(wraparound) != sync_quality_for_anomaly(reset)


# -- anomali yok ------------------------------------------------------------


def test_increasing_ticks_produce_no_anomaly() -> None:
    assert detect_tick_anomaly(1000, 2000, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=1) is None


def test_equal_ticks_produce_no_anomaly() -> None:
    """Ayni tick iki kez -- azalma yok, anomali degil (F2-011'in tekrarli
    sequence_no teshisi ayri bir konudur)."""
    assert detect_tick_anomaly(1000, 1000, COUNTER_BITS, MAX_PLAUSIBLE_DELTA, index=1) is None


def test_no_anomaly_has_good_sync_quality() -> None:
    assert sync_quality_for_anomaly(None) == SyncQuality.GOOD


# -- str ve immutability -----------------------------------------------


def test_wraparound_str_shape() -> None:
    anomaly = TickAnomaly(
        index=10,
        kind=TickAnomalyKind.WRAPAROUND,
        previous_ticks=4294967200,
        observed_ticks=50,
        unwrapped_ticks=4294967346,
    )
    assert str(anomaly) == "Sayac sarmasi: index 10, 4294967200 -> 50 (unwrap: 4294967346)"


def test_reset_str_shape() -> None:
    anomaly = TickAnomaly(
        index=20,
        kind=TickAnomalyKind.RESET,
        previous_ticks=5_000_000,
        observed_ticks=100,
        unwrapped_ticks=None,
    )
    assert str(anomaly) == "Cihaz sayaci sifirlandi: index 20, 5000000 -> 100"


def test_tick_anomaly_is_immutable() -> None:
    import dataclasses

    import pytest

    anomaly = TickAnomaly(
        index=1,
        kind=TickAnomalyKind.RESET,
        previous_ticks=1,
        observed_ticks=0,
        unwrapped_ticks=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        anomaly.index = 2  # type: ignore[misc]
