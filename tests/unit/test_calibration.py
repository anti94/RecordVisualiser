"""Calibration seçimi ve kalite eşlemesi — `F2-021`.

Kabul: eksik calibration ve geçersiz örnek kalite bilgisini korur.
"""

from __future__ import annotations

import math

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.io.decoders.calibration import (
    QualifiedSample,
    SampleQuality,
    is_calibrated,
    qualify_sample,
    sample_quality,
)
from sonar_analyzer.io.decoders.channel_catalog import CHANNELS_8


def _make_channel(*, calibration_id: str | None = None, gain: float = 1.0) -> ChannelMetadata:
    return ChannelMetadata(
        id="ch_test",
        path="Test/Channel",
        name="Test Channel",
        dtype="float32",
        calibration_id=calibration_id,
        gain=gain,
    )


# -- gecersiz ornek (NaN) kalitesi -------------------------------------------


def test_nan_raw_value_is_invalid_quality() -> None:
    """Kabul kriteri: gecersiz ornek (NaN) kalite bilgisini korur."""
    assert sample_quality(float("nan")) == SampleQuality.INVALID


def test_normal_raw_value_is_valid_quality() -> None:
    assert sample_quality(42.0) == SampleQuality.VALID
    assert sample_quality(0.0) == SampleQuality.VALID
    assert sample_quality(-3.5) == SampleQuality.VALID


def test_qualify_sample_never_converts_nan_to_zero() -> None:
    """Kabul kriteri: NaN 0.0'a cevrilmez, oldugu gibi korunur."""
    channel = _make_channel()
    result = qualify_sample(channel, float("nan"))

    assert result.quality == SampleQuality.INVALID
    assert math.isnan(result.physical_value)
    assert result.physical_value != 0.0


def test_qualify_sample_preserves_nan_through_gain_offset() -> None:
    channel = _make_channel(gain=2.0)
    result = qualify_sample(channel, float("nan"))
    assert math.isnan(result.physical_value)


# -- eksik / mevcut calibration -----------------------------------------


def test_channel_without_calibration_id_is_not_calibrated() -> None:
    """Kabul kriteri: eksik calibration kalite bilgisini korur (sessizce
    'kalibre edilmis' sayilmaz)."""
    channel = _make_channel(calibration_id=None)
    assert is_calibrated(channel) is False


def test_channel_with_calibration_id_is_calibrated() -> None:
    channel = _make_channel(calibration_id="cal-A")
    assert is_calibrated(channel) is True


def test_qualify_sample_preserves_missing_calibration() -> None:
    channel = _make_channel(calibration_id=None)
    result = qualify_sample(channel, 10.0)

    assert result.calibration_id is None
    assert result.is_calibrated is False


def test_qualify_sample_preserves_present_calibration() -> None:
    channel = _make_channel(calibration_id="cal-A")
    result = qualify_sample(channel, 10.0)

    assert result.calibration_id == "cal-A"
    assert result.is_calibrated is True


def test_valid_sample_with_missing_calibration_still_has_valid_quality() -> None:
    """Eksik kalibrasyon ve gecersiz ornek birbirinden bagimsiz bilgilerdir."""
    channel = _make_channel(calibration_id=None)
    result = qualify_sample(channel, 5.0)

    assert result.quality == SampleQuality.VALID
    assert result.is_calibrated is False


# -- F2-019 katalogunun mevcut (eksik kalibrasyon) durumu -------------------


def test_current_fixture_catalog_has_no_calibration_assigned() -> None:
    """channel-map.md: gercek kalibrasyon kataloğu gelmedi (E-04); mevcut
    katalog eksik kalibrasyonu acikca yansitir, uydurma id atamaz."""
    for channel in CHANNELS_8:
        assert channel.calibration_id is None
        assert is_calibrated(channel) is False


# -- QualifiedSample immutability -------------------------------------------


def test_qualified_sample_is_immutable() -> None:
    import dataclasses

    import pytest

    sample = QualifiedSample(physical_value=1.0, quality=SampleQuality.VALID, calibration_id=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        sample.physical_value = 2.0  # type: ignore[misc]
