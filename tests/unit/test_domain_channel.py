"""ChannelMetadata testleri — `F1-011`."""

from __future__ import annotations

import dataclasses

import pytest

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource


def make(**overrides: object) -> ChannelMetadata:
    defaults: dict[str, object] = {
        "id": "ch0",
        "path": "Acoustic/Hydrophone 1",
        "name": "Hydrophone 1",
        "dtype": "int16",
        "source": ChannelSource.ACOUSTIC,
        "unit": "Pa",
        "sample_rate_hz": 96000.0,
    }
    defaults.update(overrides)
    return ChannelMetadata(**defaults)  # type: ignore[arg-type]


def test_carries_identity_unit_dtype_and_sample_rate() -> None:
    channel = make()
    assert channel.id == "ch0"
    assert channel.unit == "Pa"
    assert channel.dtype == "int16"
    assert channel.sample_rate_hz == 96000.0
    assert channel.source is ChannelSource.ACOUSTIC


def test_display_label_includes_unit() -> None:
    assert make().display_label == "Hydrophone 1 [Pa]"


def test_display_label_without_unit() -> None:
    channel = make(unit=None)
    assert channel.display_label == "Hydrophone 1"
    assert channel.display_unit == ""


def test_sample_period_from_rate() -> None:
    assert make(sample_rate_hz=96000.0).sample_period_ns == 10417
    assert make(sample_rate_hz=8.0).sample_period_ns == 125_000_000


def test_sample_period_unknown_when_rate_missing() -> None:
    assert make(sample_rate_hz=None).sample_period_ns is None


def test_physical_conversion_uses_gain_and_offset() -> None:
    channel = make(gain=0.5, offset=-3.0)
    assert channel.to_physical(10.0) == 2.0
    assert make().to_physical(10.0) == 10.0


def test_is_immutable() -> None:
    channel = make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        channel.id = "baska"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"id": "  "}, "kimligi bos"),
        ({"path": ""}, "yolu bos"),
        ({"dtype": "float16"}, "desteklenmeyen dtype"),
        ({"sample_rate_hz": 0.0}, "pozitif olmali"),
        ({"sample_rate_hz": -1.0}, "pozitif olmali"),
        ({"time_base_id": ""}, "time_base_id bos"),
    ],
)
def test_invalid_values_are_rejected(overrides: dict[str, object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        make(**overrides)


def test_default_time_base_and_source() -> None:
    channel = ChannelMetadata(id="ch9", path="BIT/Summary", name="BIT", dtype="uint8")
    assert channel.time_base_id == "device0"
    assert channel.source is ChannelSource.UNKNOWN
    assert channel.unit is None
