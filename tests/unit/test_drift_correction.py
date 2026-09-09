"""Tanımlı drift düzeltmesini uygulama — `F2-027`.

Kabul: bilinen katsayı referans zamanı üretir; düzeltme metadata'da görünür.
"""

from __future__ import annotations

from sonar_analyzer.domain.time_base import TimeBase
from sonar_analyzer.io.decoders.drift_correction import (
    DriftCorrectedTimestamp,
    apply_drift_correction,
)

REFERENCE_EPOCH_NS = 1_788_901_200_000_000_000


def _time_base(drift_ppm: float) -> TimeBase:
    return TimeBase(
        id="device0",
        epoch_utc_ns=REFERENCE_EPOCH_NS,
        tick_hz=10_000_000,
        source="local_oscillator",
        drift_ppm=drift_ppm,
    )


# -- kabul kriteri: bilinen katsayi referans zamani uretir -----------------


def test_known_50ppm_over_one_hour_produces_documented_180ms_correction() -> None:
    """ADR-003 §2.6: '50 ppm sapma ... 1 saatte 180 ms'."""
    time_base = _time_base(drift_ppm=50.0)
    one_hour_ns = 3_600 * 1_000_000_000
    raw_timestamp_ns = REFERENCE_EPOCH_NS + one_hour_ns

    result = apply_drift_correction(time_base, raw_timestamp_ns, REFERENCE_EPOCH_NS)

    correction_ns = result.raw_timestamp_ns - result.corrected_timestamp_ns
    assert correction_ns == 180_000_000  # 180 ms


def test_known_50ppm_over_one_period_produces_documented_6_25us_correction() -> None:
    """ADR-003 §2.6: '50 ppm sapma 125 ms'te yalnız 6,25 us'."""
    time_base = _time_base(drift_ppm=50.0)
    raw_timestamp_ns = REFERENCE_EPOCH_NS + 125_000_000  # 125 ms sonra

    result = apply_drift_correction(time_base, raw_timestamp_ns, REFERENCE_EPOCH_NS)

    correction_ns = result.raw_timestamp_ns - result.corrected_timestamp_ns
    assert correction_ns == 6_250  # 6.25 us


def test_negative_drift_ppm_corrects_in_opposite_direction() -> None:
    time_base = _time_base(drift_ppm=-50.0)
    raw_timestamp_ns = REFERENCE_EPOCH_NS + 125_000_000

    result = apply_drift_correction(time_base, raw_timestamp_ns, REFERENCE_EPOCH_NS)

    correction_ns = result.raw_timestamp_ns - result.corrected_timestamp_ns
    assert correction_ns == -6_250


def test_reference_epoch_itself_has_zero_correction() -> None:
    """elapsed=0 oldugunda duzeltme miktari da sifirdir (katsayi ne olursa olsun)."""
    time_base = _time_base(drift_ppm=50.0)
    result = apply_drift_correction(time_base, REFERENCE_EPOCH_NS, REFERENCE_EPOCH_NS)
    assert result.corrected_timestamp_ns == result.raw_timestamp_ns


# -- kabul kriteri: duzeltme metadata'da gorunur ----------------------------


def test_correction_is_visible_in_metadata_when_drift_nonzero() -> None:
    """Kabul kriteri: duzeltme metadata'da gorunur (corrected=True, drift_ppm saklanir)."""
    time_base = _time_base(drift_ppm=50.0)
    result = apply_drift_correction(time_base, REFERENCE_EPOCH_NS + 125_000_000, REFERENCE_EPOCH_NS)

    assert isinstance(result, DriftCorrectedTimestamp)
    assert result.corrected is True
    assert result.drift_ppm == 50.0
    assert result.time_base_id == "device0"
    assert result.corrected_timestamp_ns != result.raw_timestamp_ns


def test_zero_drift_ppm_is_marked_uncorrected_and_leaves_raw_untouched() -> None:
    """drift_ppm=0 -- GPS/PPS disiplinli kaynak veya olcum yok; duzeltme
    uygulanmadigi metadata'da acikca gorunur."""
    time_base = _time_base(drift_ppm=0.0)
    raw_timestamp_ns = REFERENCE_EPOCH_NS + 125_000_000

    result = apply_drift_correction(time_base, raw_timestamp_ns, REFERENCE_EPOCH_NS)

    assert result.corrected is False
    assert result.corrected_timestamp_ns == result.raw_timestamp_ns
    assert result.drift_ppm == 0.0


def test_raw_timestamp_remains_accessible_after_correction() -> None:
    """ADR-003 §2.6: ham zaman erisilebilir kalir -- sessizce yerine gecmez."""
    time_base = _time_base(drift_ppm=50.0)
    raw_timestamp_ns = REFERENCE_EPOCH_NS + 125_000_000

    result = apply_drift_correction(time_base, raw_timestamp_ns, REFERENCE_EPOCH_NS)

    assert result.raw_timestamp_ns == raw_timestamp_ns


def test_drift_corrected_timestamp_is_immutable() -> None:
    import dataclasses

    import pytest

    result = DriftCorrectedTimestamp(
        raw_timestamp_ns=1,
        corrected_timestamp_ns=1,
        drift_ppm=0.0,
        corrected=False,
        time_base_id="x",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.corrected = True  # type: ignore[misc]
