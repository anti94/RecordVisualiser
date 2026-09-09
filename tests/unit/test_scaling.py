"""Scale ve offset dönüşümü — `F2-020`.

Kabul: bilinen ham değer beklenen mühendislik değerine dönüşür.
"""

from __future__ import annotations

import pytest
from tests.golden_bytes import build_valid_fixture

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.io.decoders.channel_catalog import CHANNELS_8
from sonar_analyzer.io.decoders.profile_a import decode_record_at_index
from sonar_analyzer.io.decoders.scaling import apply_scale_offset, physical_values_for_record


def test_known_raw_value_converts_to_expected_engineering_value() -> None:
    """Kabul kriteri: raw ADC sayaci -> volt donusumu (gain=0.01, offset=-5.0)."""
    channel = ChannelMetadata(
        id="ch_test",
        path="Test/Voltage",
        name="Test Voltage",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="V",
        gain=0.01,
        offset=-5.0,
    )
    # raw=1000 sayac -> 1000 * 0.01 - 5.0 = 5.0 V
    assert apply_scale_offset(channel, 1000.0) == 5.0
    # raw=0 sayac -> 0 * 0.01 - 5.0 = -5.0 V
    assert apply_scale_offset(channel, 0.0) == -5.0


def test_identity_channel_passes_raw_value_through() -> None:
    """gain=1.0, offset=0.0 (ontanimli) icin fiziksel deger = ham deger."""
    channel = ChannelMetadata(
        id="ch_identity",
        path="Test/Identity",
        name="Identity",
        dtype="float32",
    )
    assert apply_scale_offset(channel, 42.5) == 42.5


def test_current_fixture_profile_channels_are_identity_gain_offset() -> None:
    """channel-map.md §6: mevcut profilde ham deger zaten fiziksel birimdedir."""
    for channel in CHANNELS_8:
        assert channel.gain == 1.0
        assert channel.offset == 0.0


def test_physical_values_for_record_matches_raw_with_identity_catalog() -> None:
    buffer = build_valid_fixture()
    record = decode_record_at_index(buffer, 3)

    physical = physical_values_for_record(record, CHANNELS_8)

    assert physical == record.sensor_values


def test_physical_values_for_record_applies_nontrivial_scaling() -> None:
    """Kabul kriteri: sifirdan farkli gain/offset ile bilinen deger donusur."""
    scaled_catalog = tuple(
        ChannelMetadata(
            id=f"ch{i}",
            path=f"Test/Ch{i}",
            name=f"Ch{i}",
            dtype="float32",
            gain=2.0,
            offset=10.0,
        )
        for i in range(8)
    )
    buffer = build_valid_fixture()
    record = decode_record_at_index(buffer, 1)

    physical = physical_values_for_record(record, scaled_catalog)

    expected = tuple(raw * 2.0 + 10.0 for raw in record.sensor_values)
    assert physical == expected
    assert physical != record.sensor_values


def test_physical_values_for_record_rejects_channel_count_mismatch() -> None:
    buffer = build_valid_fixture()
    record = decode_record_at_index(buffer, 0)

    with pytest.raises(ValueError, match="kanal sayisi uyusmuyor"):
        physical_values_for_record(record, CHANNELS_8[:4])
