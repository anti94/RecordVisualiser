"""RecordingRepository sözleşmesi testleri — `F1-016`."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import BitResult, BitState, Event, Severity
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval, TxState
from sonar_analyzer.repository.protocol import EventFilter, RecordingRepository

SECOND = 1_000_000_000


class FakeRepository:
    """Sözleşmeyi karşılayan en küçük gerçekleme; testlerde ölçüt olarak kullanılır."""

    def __init__(self) -> None:
        self.closed = False
        self._channels = [
            ChannelMetadata(
                id="ch0",
                path="Acoustic/Hydrophone 1",
                name="Hydrophone 1",
                dtype="float32",
                source=ChannelSource.ACOUSTIC,
                unit="Pa",
                sample_rate_hz=8.0,
            )
        ]
        self._events = [
            Event(
                timestamp_ns=500_000_000,
                source="BIT",
                category="Thermal",
                severity=Severity.ERROR,
                code="0x0412",
                message="Amplifikator sicakligi yuksek",
            ),
            Event(
                timestamp_ns=750_000_000,
                source="System",
                category="Parser",
                severity=Severity.INFO,
                code="0",
                message="Kayit acildi",
            ),
        ]

    def metadata(self) -> RecordingMetadata:
        return RecordingMetadata(
            recording_id="rec-001",
            source_path="D:/kayitlar/ornek.bin",
            time_range=TimeRange(0, SECOND),
            channel_count=1,
            record_count=8,
        )

    def channels(self) -> Sequence[ChannelMetadata]:
        return self._channels

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        step = 125_000_000
        stamps = np.arange(time_range.start_ns, time_range.end_ns, step, dtype=np.int64)
        if max_points is not None and stamps.size > max_points:
            stride = int(np.ceil(stamps.size / max_points))
            stamps = stamps[::stride]
        return DataChunk(
            channel_id=channel_id,
            timestamps_ns=stamps,
            values=np.arange(stamps.size, dtype=np.float32),
        )

    def events(
        self,
        time_range: TimeRange,
        filters: EventFilter | None = None,
    ) -> Sequence[Event]:
        selected = [e for e in self._events if time_range.contains(e.timestamp_ns)]
        if filters is not None:
            selected = [e for e in selected if filters.matches(e)]
        return sorted(selected, key=lambda e: e.timestamp_ns)

    def bit_results(self, time_range: TimeRange) -> Sequence[BitResult]:
        result = BitResult(
            timestamp_ns=500_000_000,
            test_id=8,
            component="Thermal Management",
            state=BitState.FAIL,
            severity=Severity.ERROR,
        )
        return [result] if time_range.contains(result.timestamp_ns) else []

    def transmissions(self, time_range: TimeRange) -> Sequence[TransmissionInterval]:
        interval = TransmissionInterval(time_range=TimeRange(250_000_000, 750_000_000))
        return [interval] if interval.time_range.overlaps(time_range) else []

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def repo() -> FakeRepository:
    return FakeRepository()


def test_fake_satisfies_protocol(repo: FakeRepository) -> None:
    assert isinstance(repo, RecordingRepository)


def test_metadata_returns_domain_type(repo: FakeRepository) -> None:
    meta = repo.metadata()
    assert isinstance(meta, RecordingMetadata)
    assert meta.time_range == TimeRange(0, SECOND)


def test_channels_return_domain_type(repo: FakeRepository) -> None:
    channels = repo.channels()
    assert all(isinstance(c, ChannelMetadata) for c in channels)
    assert channels[0].unit == "Pa"


def test_query_returns_data_chunk(repo: FakeRepository) -> None:
    chunk = repo.query("ch0", TimeRange(0, SECOND))
    assert isinstance(chunk, DataChunk)
    assert len(chunk) == 8
    assert chunk.channel_id == "ch0"


def test_query_respects_max_points(repo: FakeRepository) -> None:
    chunk = repo.query("ch0", TimeRange(0, SECOND), max_points=3)
    assert len(chunk) <= 3
    assert len(chunk) > 0


def test_query_outside_data_returns_empty_chunk(repo: FakeRepository) -> None:
    chunk = repo.query("ch0", TimeRange(10 * SECOND, 10 * SECOND))
    assert chunk.is_empty, "veri yoksa hata degil, bos parca donmeli"


def test_events_sorted_and_filtered(repo: FakeRepository) -> None:
    events = repo.events(TimeRange(0, SECOND))
    assert [e.timestamp_ns for e in events] == [500_000_000, 750_000_000]

    only_bit = repo.events(TimeRange(0, SECOND), EventFilter(sources=["BIT"]))
    assert len(only_bit) == 1
    assert only_bit[0].source == "BIT"


def test_event_filter_by_min_severity(repo: FakeRepository) -> None:
    events = repo.events(TimeRange(0, SECOND), EventFilter(min_severity=Severity.ERROR))
    assert len(events) == 1
    assert events[0].severity is Severity.ERROR


def test_event_filter_by_text_is_case_insensitive(repo: FakeRepository) -> None:
    events = repo.events(TimeRange(0, SECOND), EventFilter(text="SICAKLIGI"))
    assert len(events) == 1


def test_empty_filter_accepts_everything(repo: FakeRepository) -> None:
    assert len(repo.events(TimeRange(0, SECOND), EventFilter())) == 2


def test_bit_results_and_transmissions(repo: FakeRepository) -> None:
    bits = repo.bit_results(TimeRange(0, SECOND))
    assert bits[0].state is BitState.FAIL

    intervals = repo.transmissions(TimeRange(0, SECOND))
    assert intervals[0].state is TxState.ACTIVE
    assert repo.transmissions(TimeRange(5 * SECOND, 6 * SECOND)) == []


def test_close(repo: FakeRepository) -> None:
    repo.close()
    assert repo.closed


def test_incomplete_implementation_is_not_a_repository() -> None:
    class Missing:
        def metadata(self) -> None: ...

    assert not isinstance(Missing(), RecordingRepository)
