"""Canlı akış ortak repository sözleşmesinde — `F5-021`.

Kabul: aynı kanal ve olay sorguları dosya ve canlı kaynakta çalışır.

En güçlü kanıt çapraz doğrulamadır: bir `MockRecordingRepository`
(kayıtlı kaynak) `FileReplaySource` ile paketlere çevrilip
`LiveRepository`'ye akıtılır, sonra **aynı sorgu** iki kaynağa da
sorulur. Sonuçlar birbirine eşit olmalı — "aynı ekran, farklı kaynak"
iddiası ancak böyle kanıtlanır.
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.io.live.ring_buffer import LiveRingBuffer
from sonar_analyzer.repository.live_repository import LIVE_LABEL, LiveRepository
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.repository.protocol import EventFilter, RecordingRepository

DURATION_S = 1.0


def _recorded() -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=DURATION_S)


def _live_from(recorded: MockRecordingRepository, *, capacity: int = 100_000) -> LiveRepository:
    """Kayıtlı kaynağı canlı paketlere çevirip canlı repository'ye akıtır."""
    source = FileReplaySource(recorded, sleep=lambda _s: None)
    source.connect()
    live = LiveRepository(LiveRingBuffer(capacity_samples=capacity), channels=recorded.channels())
    for packet in source.packets():
        live.ingest(packet)
    return live


def _chunk(channel_id: str, first: int, n: int) -> DataChunk:
    timestamps = np.arange(first, first + n, dtype=np.int64)
    return DataChunk(channel_id, timestamps, timestamps.astype(np.float64))


def _event(timestamp_ns: int, source: str = "live") -> Event:
    return Event(
        timestamp_ns=timestamp_ns,
        source=source,
        category="sistem",
        severity=Severity.INFO,
        code="",
        message="olay",
    )


# --------------------------------------------------------------------------- #
# ortak sozlesme
# --------------------------------------------------------------------------- #


def test_it_satisfies_the_recording_repository_protocol() -> None:
    live = LiveRepository(LiveRingBuffer(capacity_samples=10))
    assert isinstance(live, RecordingRepository)


def test_the_source_path_says_live_not_simulation() -> None:
    """Kullanıcı verinin nereden geldiğini görür — canlı, simülasyon değil."""
    live = LiveRepository(LiveRingBuffer(capacity_samples=10))
    assert live.metadata().source_path == LIVE_LABEL


def test_an_empty_live_repository_answers_without_raising() -> None:
    live = LiveRepository(LiveRingBuffer(capacity_samples=10))
    assert len(live.query("ch0", TimeRange(0, 1000))) == 0
    assert live.events(TimeRange(0, 1000)) == []
    assert live.metadata().record_count == 0


# --------------------------------------------------------------------------- #
# CAPRAZ DOGRULAMA: ayni sorgu, iki kaynak, ayni sonuc
# --------------------------------------------------------------------------- #


def _both_sources() -> tuple[MockRecordingRepository, LiveRepository]:
    recorded = _recorded()
    return recorded, _live_from(recorded)


@pytest.mark.parametrize("channel_id", ["ch0", "ch3", "ch7"])
def test_the_same_channel_query_gives_the_same_data_from_both_sources(channel_id: str) -> None:
    recorded, live = _both_sources()
    window = recorded.metadata().time_range

    from_file = recorded.query(channel_id, window)
    from_live = live.query(channel_id, window)

    assert from_live.timestamps_ns.tolist() == from_file.timestamps_ns.tolist()
    assert from_live.values.tolist() == from_file.values.tolist()


def test_a_narrowed_window_matches_on_both_sources() -> None:
    recorded, live = _both_sources()
    span = recorded.metadata().time_range
    quarter = span.duration_ns // 4
    window = TimeRange(span.start_ns + quarter, span.start_ns + 3 * quarter)

    from_file = recorded.query("ch0", window)
    from_live = live.query("ch0", window)
    assert from_live.timestamps_ns.tolist() == from_file.timestamps_ns.tolist()
    assert len(from_live) > 0  # test gercekten bir sey olcuyor


def test_the_same_event_query_gives_the_same_events_from_both_sources() -> None:
    recorded, live = _both_sources()
    window = recorded.metadata().time_range

    from_file = list(recorded.events(window))
    from_live = list(live.events(window))

    assert [(e.timestamp_ns, e.source, e.code) for e in from_live] == [
        (e.timestamp_ns, e.source, e.code) for e in from_file
    ]
    assert from_live  # olay gercekten var


def test_an_event_filter_works_the_same_on_both_sources() -> None:
    recorded, live = _both_sources()
    window = recorded.metadata().time_range
    filters = EventFilter(min_severity=Severity.ERROR)

    from_file = list(recorded.events(window, filters))
    from_live = list(live.events(window, filters))
    assert [e.timestamp_ns for e in from_live] == [e.timestamp_ns for e in from_file]


def test_max_points_downsampling_works_on_the_live_source_too() -> None:
    recorded, live = _both_sources()
    window = recorded.metadata().time_range

    reduced = live.query("ch0", window, max_points=4)
    assert 0 < len(reduced) <= 4


# --------------------------------------------------------------------------- #
# canli kaynaga ozgu davranis
# --------------------------------------------------------------------------- #


def test_the_time_range_grows_as_packets_arrive() -> None:
    """Dosyadan tek fark: canlı aralık sabit değil, akış sürdükçe büyür."""
    live = LiveRepository(LiveRingBuffer(capacity_samples=1000))
    live.ingest(LivePacket(sequence_no=0, received_ns=0, chunks=[_chunk("ch0", 0, 10)]))
    first = live.metadata().time_range

    live.ingest(LivePacket(sequence_no=1, received_ns=1, chunks=[_chunk("ch0", 10, 10)]))
    second = live.metadata().time_range

    assert second.end_ns > first.end_ns
    assert second.start_ns == first.start_ns


def test_the_span_covers_every_channel() -> None:
    live = LiveRepository(LiveRingBuffer(capacity_samples=1000))
    live.ingest(
        LivePacket(
            sequence_no=0,
            received_ns=0,
            chunks=[_chunk("ch0", 100, 5), _chunk("ch1", 0, 5)],
        )
    )
    span = live.metadata().time_range
    assert span.start_ns == 0  # en erken kanal
    assert span.end_ns == 105  # en gec kanal + 1


def test_the_record_count_follows_ingested_packets() -> None:
    live = LiveRepository(LiveRingBuffer(capacity_samples=100))
    for index in range(3):
        live.ingest(
            LivePacket(sequence_no=index, received_ns=index, chunks=[_chunk("ch0", index, 1)])
        )
    assert live.metadata().record_count == 3
    assert live.packet_count == 3


def test_ingest_reports_ring_buffer_eviction() -> None:
    live = LiveRepository(LiveRingBuffer(capacity_samples=10))
    assert live.ingest(LivePacket(0, 0, chunks=[_chunk("ch0", 0, 6)])) == 0
    assert live.ingest(LivePacket(1, 1, chunks=[_chunk("ch0", 6, 8)])) == 4


def test_old_samples_leave_the_query_result_after_eviction() -> None:
    live = LiveRepository(LiveRingBuffer(capacity_samples=5))
    live.ingest(LivePacket(0, 0, chunks=[_chunk("ch0", 0, 20)]))

    result = live.query("ch0", TimeRange(0, 100))
    assert result.timestamps_ns.tolist() == [15, 16, 17, 18, 19]


# --------------------------------------------------------------------------- #
# olaylar: bellek sinirli, siralı
# --------------------------------------------------------------------------- #


def test_events_are_returned_in_time_order_regardless_of_arrival() -> None:
    live = LiveRepository(LiveRingBuffer(capacity_samples=100))
    live.ingest(LivePacket(0, 0, events=[_event(50), _event(10)]))
    live.ingest(LivePacket(1, 1, events=[_event(30)]))

    stamps = [event.timestamp_ns for event in live.events(TimeRange(0, 100))]
    assert stamps == [10, 30, 50]


def test_the_event_queue_is_bounded() -> None:
    """Canlı oturum saatlerce sürse de olay listesi büyümez."""
    live = LiveRepository(LiveRingBuffer(capacity_samples=10), event_capacity=5)
    for index in range(50):
        live.ingest(LivePacket(index, index, events=[_event(index)]))

    held = live.events(TimeRange(0, 1000))
    assert len(held) == 5
    assert [event.timestamp_ns for event in held] == [45, 46, 47, 48, 49]  # en yeniler


def test_event_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="event_capacity pozitif olmali"):
        LiveRepository(LiveRingBuffer(capacity_samples=10), event_capacity=0)


# --------------------------------------------------------------------------- #
# tasimadigi veriyi UYDURMAZ
# --------------------------------------------------------------------------- #


def test_bit_results_stay_empty_when_the_source_reports_none() -> None:
    """BIT bildirmeyen kaynakta sonuç **uydurulmaz**.

    `F5-034` ile `LivePacket` BIT taşıyabiliyor; taşımadığında liste boş
    kalır — doldurmak, arızasız görünen uydurma bir pano demek olurdu.
    """
    _recorded_repo, live = _both_sources()
    assert list(live.bit_results(TimeRange(0, 10**12))) == []


def test_transmissions_stay_empty_for_the_same_reason() -> None:
    _recorded_repo, live = _both_sources()
    assert list(live.transmissions(TimeRange(0, 10**12))) == []


# --------------------------------------------------------------------------- #
# kapatma
# --------------------------------------------------------------------------- #


def test_close_releases_the_buffer_and_refuses_further_queries() -> None:
    _recorded_repo, live = _both_sources()
    live.close()

    with pytest.raises(RuntimeError, match="Repository kapatildi"):
        live.query("ch0", TimeRange(0, 10**12))
    with pytest.raises(RuntimeError, match="Repository kapatildi"):
        live.ingest(LivePacket(0, 0, chunks=[_chunk("ch0", 0, 1)]))


def test_close_clears_the_events() -> None:
    _recorded_repo, live = _both_sources()
    live.close()
    assert live.events(TimeRange(0, 10**12)) == []
