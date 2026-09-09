"""Sensör alanlarını kanal metadata'sına eşleme — `F2-019`.

Kabul: CH0–CH7 sırası, dtype ve birimler sözlükle eşleşir
(`docs/format/channel-map.md` §2).
"""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.channel import ChannelSource
from sonar_analyzer.io.decoders.channel_catalog import (
    CHANNELS_8,
    channel_metadata_for_slot,
)
from sonar_analyzer.io.profile_a_format import EXPECTED_CHANNEL_COUNT

#: docs/format/channel-map.md §2 — (path, unit) sırasıyla CH0-CH7.
_DOCUMENTED_PATH_AND_UNIT = (
    ("Sensors/Pressure", "bar"),
    ("Sensors/Temperature", "°C"),
    ("Sensors/Accelerometer/X", "g"),
    ("Sensors/Accelerometer/Y", "g"),
    ("Sensors/Accelerometer/Z", "g"),
    ("Acoustic/Hydrophone 1", "Pa"),
    ("Navigation/Depth", "m"),
    ("Vehicle/Voltage", "V"),
)


def test_catalog_has_exactly_eight_channels() -> None:
    assert len(CHANNELS_8) == 8
    assert len(CHANNELS_8) == EXPECTED_CHANNEL_COUNT


def test_ch0_to_ch7_order_matches_documented_dictionary() -> None:
    """Kabul kriteri: CH0-CH7 sirasi sozlukle eslesir."""
    for slot, (expected_path, _expected_unit) in enumerate(_DOCUMENTED_PATH_AND_UNIT):
        assert CHANNELS_8[slot].path == expected_path


def test_units_match_documented_dictionary() -> None:
    """Kabul kriteri: birimler sozlukle eslesir."""
    for slot, (_expected_path, expected_unit) in enumerate(_DOCUMENTED_PATH_AND_UNIT):
        assert CHANNELS_8[slot].unit == expected_unit


def test_dtype_is_float32_for_all_channels() -> None:
    """Kabul kriteri: dtype sozlukle eslesir — sensor_values her zaman float32'dir
    (DATA_RECORD_V1/V2 struct format harfi '8f')."""
    for channel in CHANNELS_8:
        assert channel.dtype == "float32"


def test_channel_ids_are_unique_and_slot_ordered() -> None:
    ids = [channel.id for channel in CHANNELS_8]
    assert ids == [f"ch{i}" for i in range(8)]
    assert len(set(ids)) == len(ids)


def test_channel_metadata_for_slot_returns_matching_entry() -> None:
    for slot in range(8):
        assert channel_metadata_for_slot(slot) is CHANNELS_8[slot]


def test_channel_metadata_for_slot_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="gecersiz kanal slotu"):
        channel_metadata_for_slot(8)
    with pytest.raises(ValueError, match="gecersiz kanal slotu"):
        channel_metadata_for_slot(-1)


def test_acoustic_channel_sources_match_group_column() -> None:
    """docs/format/channel-map.md §2 'Grup' sutunu ile ChannelSource eslesmesi."""
    assert CHANNELS_8[0].source == ChannelSource.SENSORS  # Pressure
    assert CHANNELS_8[5].source == ChannelSource.ACOUSTIC  # Hydrophone 1
    assert CHANNELS_8[6].source == ChannelSource.NAVIGATION  # Depth
    assert CHANNELS_8[7].source == ChannelSource.TRANSMISSION  # Voltage


def test_all_channels_share_the_8hz_effective_sample_rate() -> None:
    """Profil A tum kanallar icin ayni kayit periyodunu (125ms = 8Hz) paylasir."""
    for channel in CHANNELS_8:
        assert channel.sample_rate_hz == 8.0
