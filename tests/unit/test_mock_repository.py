"""Sahte repository testleri — `F1-020`."""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.repository.mock_repository import (
    SIMULATION_LABEL,
    MockRecordingRepository,
)
from sonar_analyzer.repository.protocol import RecordingRepository

SECOND = 1_000_000_000


@pytest.fixture()
def repo() -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=10.0)


def test_satisfies_repository_protocol(repo: MockRecordingRepository) -> None:
    assert isinstance(repo, RecordingRepository)


def test_metadata_declares_simulation(repo: MockRecordingRepository) -> None:
    """Sahte veri gerçek kayıt gibi sunulmamalı."""
    meta = repo.metadata()
    assert meta.source_path == SIMULATION_LABEL
    assert SIMULATION_LABEL in meta.recording_id
    assert meta.device_id == SIMULATION_LABEL


def test_metadata_time_range_and_record_count(repo: MockRecordingRepository) -> None:
    meta = repo.metadata()
    assert meta.time_range == TimeRange(0, 10 * SECOND)
    assert meta.duration_seconds == 10.0
    assert meta.record_count == 80  # 10 s x 8 kayit/s
    assert meta.channel_count == 8


def test_channels_match_channel_map(repo: MockRecordingRepository) -> None:
    channels = repo.channels()
    assert len(channels) == 8
    assert all(isinstance(c, ChannelMetadata) for c in channels)
    assert [c.id for c in channels] == [f"ch{i}" for i in range(8)]
    assert channels[0].path == "Sensors/Pressure"
    assert channels[0].unit == "bar"
    assert channels[5].path == "Acoustic/Hydrophone 1"


def test_channel_sample_rate_is_record_rate(repo: MockRecordingRepository) -> None:
    """Profil A'da kayıt başına tek değer var: 8 Hz."""
    assert repo.channels()[0].sample_rate_hz == 8.0


def test_query_full_range_returns_all_samples(repo: MockRecordingRepository) -> None:
    chunk = repo.query("ch0", TimeRange(0, 10 * SECOND))
    assert isinstance(chunk, DataChunk)
    assert len(chunk) == 80
    assert chunk.start_ns == 0
    assert chunk.end_ns == 79 * RECORD_PERIOD_NS


def test_query_subrange_returns_expected_samples(repo: MockRecordingRepository) -> None:
    """Bir saniyelik pencere tam 8 örnek içermeli."""
    chunk = repo.query("ch0", TimeRange(2 * SECOND, 3 * SECOND))
    assert len(chunk) == 8
    assert chunk.start_ns == 2 * SECOND
    assert chunk.end_ns == 3 * SECOND - RECORD_PERIOD_NS
    assert all(2 * SECOND <= t < 3 * SECOND for t in chunk.timestamps_ns.tolist())


def test_query_boundaries_are_half_open(repo: MockRecordingRepository) -> None:
    """Bitiş sınırındaki örnek sonuca girmemeli."""
    chunk = repo.query("ch0", TimeRange(0, RECORD_PERIOD_NS))
    assert len(chunk) == 1
    assert chunk.timestamps_ns[0] == 0


def test_query_outside_data_returns_empty_chunk(repo: MockRecordingRepository) -> None:
    chunk = repo.query("ch0", TimeRange(100 * SECOND, 110 * SECOND))
    assert chunk.is_empty
    assert chunk.channel_id == "ch0"


def test_query_respects_max_points(repo: MockRecordingRepository) -> None:
    chunk = repo.query("ch0", TimeRange(0, 10 * SECOND), max_points=10)
    assert len(chunk) <= 10
    assert len(chunk) > 0
    assert chunk.is_monotonic


def test_max_points_larger_than_data_changes_nothing(repo: MockRecordingRepository) -> None:
    full = repo.query("ch0", TimeRange(0, 10 * SECOND))
    limited = repo.query("ch0", TimeRange(0, 10 * SECOND), max_points=1000)
    assert np.array_equal(full.values, limited.values)


def test_query_is_deterministic(repo: MockRecordingRepository) -> None:
    first = repo.query("ch5", TimeRange(0, 5 * SECOND))
    second = MockRecordingRepository(duration_s=10.0).query("ch5", TimeRange(0, 5 * SECOND))
    assert first.values.tobytes() == second.values.tobytes()


def test_different_seed_changes_noisy_channel() -> None:
    first = MockRecordingRepository(duration_s=5.0, seed=1).query("ch5", TimeRange(0, 5 * SECOND))
    second = MockRecordingRepository(duration_s=5.0, seed=2).query("ch5", TimeRange(0, 5 * SECOND))
    assert not np.array_equal(first.values, second.values)


def test_values_are_around_expected_offset(repo: MockRecordingRepository) -> None:
    """Basınç kanalı 100 bar civarında salınmalı (offset 100, genlik 20)."""
    chunk = repo.query("ch0", TimeRange(0, 10 * SECOND))
    assert float(chunk.values.min()) >= 80.0
    assert float(chunk.values.max()) <= 120.0


def test_unknown_channel_raises(repo: MockRecordingRepository) -> None:
    with pytest.raises(KeyError, match="Bilinmeyen kanal"):
        repo.query("yok", TimeRange(0, SECOND))


def test_query_after_close_raises(repo: MockRecordingRepository) -> None:
    repo.close()
    with pytest.raises(RuntimeError, match="kapatildi"):
        repo.query("ch0", TimeRange(0, SECOND))


def test_events_bit_and_transmissions_are_empty_for_now(
    repo: MockRecordingRepository,
) -> None:
    """F1-021'e kadar olay üretilmiyor; boş liste dönüyor, hata değil."""
    span = TimeRange(0, 10 * SECOND)
    assert repo.events(span) == []
    assert repo.bit_results(span) == []
    assert repo.transmissions(span) == []


def test_rejects_non_positive_duration() -> None:
    with pytest.raises(ValueError, match="Sure pozitif"):
        MockRecordingRepository(duration_s=0.0)


def test_start_offset_is_respected() -> None:
    repo = MockRecordingRepository(duration_s=2.0, start_ns=5 * SECOND)
    meta = repo.metadata()
    assert meta.start_ns == 5 * SECOND
    chunk = repo.query("ch0", TimeRange(5 * SECOND, 6 * SECOND))
    assert chunk.start_ns == 5 * SECOND
