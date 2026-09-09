"""Kanal indeksini oluşturma — `F2-029`.

Kabul: kanal sorgusu referans sayıları verir.
"""

from __future__ import annotations

from tests.golden_bytes import START_TIME_UTC_NS, build_valid_fixture

from sonar_analyzer.io.decoders.channel_catalog import CHANNELS_8
from sonar_analyzer.io.index.channel_index import ChannelIndexEntry, build_channel_index
from sonar_analyzer.io.index.record_index import build_record_index
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

PERIOD_NS = 125_000_000
CHANNEL_IDS = tuple(channel.id for channel in CHANNELS_8)


def test_every_channel_has_full_sample_count_in_dense_profile() -> None:
    """Kabul kriteri: kanal sorgusu referans sayıları verir (Profil A yoğundur)."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    record_entries = build_record_index(buffer, header)

    channel_index = build_channel_index(record_entries, CHANNEL_IDS)

    assert set(channel_index) == set(CHANNEL_IDS)
    for channel_id in CHANNEL_IDS:
        assert channel_index[channel_id].sample_count == 8


def test_channel_index_time_range_matches_recording_span() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    record_entries = build_record_index(buffer, header)

    channel_index = build_channel_index(record_entries, CHANNEL_IDS)

    for channel_id in CHANNEL_IDS:
        entry = channel_index[channel_id]
        assert entry.first_timestamp_ns == START_TIME_UTC_NS
        assert entry.last_timestamp_ns == START_TIME_UTC_NS + 7 * PERIOD_NS


def test_channel_index_is_empty_for_header_only_buffer() -> None:
    buffer = build_valid_fixture(record_count=0)
    header = read_file_header_v1(buffer)
    record_entries = build_record_index(buffer, header)

    channel_index = build_channel_index(record_entries, CHANNEL_IDS)

    for channel_id in CHANNEL_IDS:
        entry = channel_index[channel_id]
        assert entry.sample_count == 0
        assert entry.first_timestamp_ns is None
        assert entry.last_timestamp_ns is None


def test_channel_index_entry_is_immutable() -> None:
    import dataclasses

    import pytest

    entry = ChannelIndexEntry(
        channel_id="ch0", sample_count=1, first_timestamp_ns=0, last_timestamp_ns=0
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.sample_count = 2  # type: ignore[misc]
