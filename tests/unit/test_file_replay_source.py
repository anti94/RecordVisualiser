"""Dosyadan replay `LiveSource` adaptörü — `F5-003`.

Kabul: 125 ms kayıtlar seçilen hızla aynı domain akışını üretir.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import Event
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveSource
from sonar_analyzer.repository.mock_repository import MockRecordingRepository


def _snapshot(packet: LivePacket) -> tuple[object, ...]:
    """Karşılaştırılabilir içerik — numpy dizileri `==` ile kıyaslanamaz."""
    chunks = tuple(
        (chunk.channel_id, chunk.timestamps_ns.tolist(), chunk.values.tolist())
        for chunk in packet.chunks
    )
    events = tuple((event.timestamp_ns, event.source, event.code) for event in packet.events)
    return (packet.sequence_no, chunks, events)


class _SleepSpy:
    """Gerçekten uyumaz; her çağrının süresini kaydeder."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _repository(duration_s: float = 1.0, **kwargs: Any) -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=duration_s, **kwargs)


# --------------------------------------------------------------------------- #
# pencereleme ve icerik
# --------------------------------------------------------------------------- #


def test_produces_one_packet_per_125ms_window() -> None:
    repository = _repository(duration_s=1.0)  # 1e9 ns / 125e6 ns = 8 tam pencere
    source = FileReplaySource(repository, sleep=_SleepSpy())
    source.connect()
    packets = list(source.packets())
    assert len(packets) == 8
    assert [p.sequence_no for p in packets] == list(range(8))


def test_a_partial_final_window_is_still_produced() -> None:
    repository = _repository(duration_s=0.3)  # 300 ms -> 125,125,50 ms
    source = FileReplaySource(repository, sleep=_SleepSpy())
    source.connect()
    packets = list(source.packets())
    assert len(packets) == 3


def test_packet_content_matches_a_direct_repository_query() -> None:
    repository = _repository(duration_s=1.0)
    source = FileReplaySource(repository, sleep=_SleepSpy())
    source.connect()
    packets = list(source.packets())

    channel_ids = [channel.id for channel in repository.channels()]
    for index, packet in enumerate(packets):
        window = TimeRange(index * RECORD_PERIOD_NS, (index + 1) * RECORD_PERIOD_NS)
        expected_chunks = {
            channel_id: repository.query(channel_id, window) for channel_id in channel_ids
        }
        seen = {chunk.channel_id for chunk in packet.chunks}
        for chunk in packet.chunks:
            expected = expected_chunks[chunk.channel_id]
            assert chunk.timestamps_ns.tolist() == expected.timestamps_ns.tolist()
            assert chunk.values.tolist() == expected.values.tolist()
        # Bu pencerede veri taşımayan kanal payload'a hiç girmez.
        for channel_id, expected in expected_chunks.items():
            assert (channel_id in seen) == (len(expected) > 0)


def test_events_appear_in_their_own_window_only() -> None:
    """BIT/sistem olayları `bit_period_s=1.0`, t=0'da; ilk pencerede olmalı."""
    repository = _repository(duration_s=1.0)
    source = FileReplaySource(repository, sleep=_SleepSpy())
    source.connect()
    packets = list(source.packets())

    assert len(packets[0].events) > 0  # 8 BIT sonucu + sistem olayi, t=0
    assert all(0 <= event.timestamp_ns < RECORD_PERIOD_NS for event in packets[0].events)
    for packet in packets[1:4]:  # 125..500 ms araliginda planli olay yok
        assert packet.events == []


def test_no_data_channel_is_reported_as_an_empty_dropped_free_stream() -> None:
    """Boş bir kanal payload'a hiç girmez; bu bir kayıp değil, tasarımdır."""
    repository = _repository(duration_s=1.0)
    source = FileReplaySource(repository, sleep=_SleepSpy())
    source.connect()
    for packet in source.packets():
        assert all(len(chunk) > 0 for chunk in packet.chunks)
    assert source.stats().dropped_packets == 0


# --------------------------------------------------------------------------- #
# hiz: icerigi degil yalnizca araligi olcekler
# --------------------------------------------------------------------------- #


def test_speed_does_not_change_the_produced_content() -> None:
    slow = FileReplaySource(_repository(duration_s=0.5), speed=1.0, sleep=_SleepSpy())
    fast = FileReplaySource(_repository(duration_s=0.5), speed=8.0, sleep=_SleepSpy())
    slow.connect()
    fast.connect()

    slow_snapshots = [_snapshot(p) for p in slow.packets()]
    fast_snapshots = [_snapshot(p) for p in fast.packets()]
    assert slow_snapshots == fast_snapshots


def test_speed_scales_the_sleep_duration_between_packets() -> None:
    spy_slow, spy_fast = _SleepSpy(), _SleepSpy()
    slow = FileReplaySource(_repository(duration_s=0.5), speed=1.0, sleep=spy_slow)
    fast = FileReplaySource(_repository(duration_s=0.5), speed=4.0, sleep=spy_fast)
    slow.connect()
    fast.connect()
    list(slow.packets())
    list(fast.packets())

    expected_slow = RECORD_PERIOD_NS / 1_000_000_000 / 1.0
    expected_fast = RECORD_PERIOD_NS / 1_000_000_000 / 4.0
    assert all(abs(call - expected_slow) < 1e-9 for call in spy_slow.calls)
    assert all(abs(call - expected_fast) < 1e-9 for call in spy_fast.calls)
    # Ayni pencere sayisi: toplam uyku suresi tam 4x farkli olmali.
    assert abs(sum(spy_slow.calls) - sum(spy_fast.calls) * 4) < 1e-9


def test_real_time_pacing_end_to_end_at_high_speed() -> None:
    """Gerçek `time.sleep` ile: yüksek hızda küçük bir kayıt hızla biter."""
    repository = _repository(duration_s=0.5)  # 4 pencere
    source = FileReplaySource(repository, speed=1000.0, sleep=time.sleep)
    source.connect()
    started = time.perf_counter()
    packets = list(source.packets())
    elapsed = time.perf_counter() - started
    assert len(packets) == 4
    # 4 * 0.125 / 1000 = 0.5 ms nominal; gevsek bir ust sinir (isletim sistemi payi).
    assert elapsed < 0.5


# --------------------------------------------------------------------------- #
# baglanti durumu ve sozlesme
# --------------------------------------------------------------------------- #


def test_satisfies_the_live_source_protocol() -> None:
    source = FileReplaySource(_repository(), sleep=_SleepSpy())
    assert isinstance(source, LiveSource)


def test_starts_disconnected_and_connect_reaches_connected() -> None:
    source = FileReplaySource(_repository(), sleep=_SleepSpy())
    assert source.state is ConnectionState.DISCONNECTED
    source.connect()
    assert source.state is ConnectionState.CONNECTED


def test_connect_and_disconnect_are_idempotent() -> None:
    source = FileReplaySource(_repository(), sleep=_SleepSpy())
    source.connect()
    source.connect()
    assert source.state is ConnectionState.CONNECTED
    source.disconnect()
    source.disconnect()
    assert source.state is ConnectionState.DISCONNECTED


def test_packets_before_connect_yield_nothing() -> None:
    source = FileReplaySource(_repository(duration_s=1.0), sleep=_SleepSpy())
    assert list(source.packets()) == []


def test_channels_delegates_to_the_repository() -> None:
    repository = _repository()
    source = FileReplaySource(repository, sleep=_SleepSpy())
    assert list(source.channels()) == list(repository.channels())


def test_stats_track_received_count_and_last_sequence() -> None:
    source = FileReplaySource(_repository(duration_s=0.5), sleep=_SleepSpy())
    source.connect()
    list(source.packets())
    stats = source.stats()
    assert stats.received_packets == 4
    assert stats.dropped_packets == 0
    assert stats.last_sequence_no == 3


def test_speed_must_be_positive() -> None:
    with pytest.raises(ValueError, match="speed pozitif olmali"):
        FileReplaySource(_repository(), speed=0.0)
    with pytest.raises(ValueError, match="speed pozitif olmali"):
        FileReplaySource(_repository(), speed=-1.0)


# --------------------------------------------------------------------------- #
# durdurma / kesme (temel — ayrintili zamanlama F5-004)
# --------------------------------------------------------------------------- #


def test_disconnect_stops_the_generator_without_a_further_packet() -> None:
    source = FileReplaySource(_repository(duration_s=1.0), sleep=_SleepSpy())
    source.connect()
    iterator = source.packets()
    first = next(iterator)
    assert first.sequence_no == 0

    source.disconnect()
    with pytest.raises(StopIteration):
        next(iterator)


def test_stop_ends_the_current_generator_but_a_new_call_restarts_from_zero() -> None:
    source = FileReplaySource(_repository(duration_s=1.0), sleep=_SleepSpy())
    source.connect()
    iterator = source.packets()
    assert next(iterator).sequence_no == 0
    assert next(iterator).sequence_no == 1

    source.stop()
    with pytest.raises(StopIteration):
        next(iterator)

    restarted = source.packets()
    assert next(restarted).sequence_no == 0


def test_pause_blocks_packets_until_resumed() -> None:
    """Duraklatmayken hiçbir paket yayınlanmaz (`F5-004` kabul kriterinin temeli)."""
    calls: list[int] = []

    def sleep_then_resume(_seconds: float) -> None:
        calls.append(0)
        if len(calls) >= 3:  # birkac uyku turundan sonra dis etken devam ettirir
            source.resume()

    source = FileReplaySource(_repository(duration_s=1.0), sleep=sleep_then_resume)
    source.connect()
    source.pause()
    iterator = source.packets()
    packet = next(iterator)  # pause() -> birkac sleep -> resume() -> ilk paket
    assert packet.sequence_no == 0
    assert len(calls) >= 3


def test_typed_chunk_and_event_classes_are_used() -> None:
    """Payload gerçek domain tipleri taşır — yer tutucu bayt yığını değil."""
    repository = _repository(duration_s=1.0)
    source = FileReplaySource(repository, sleep=_SleepSpy())
    source.connect()
    first = next(iter(source.packets()))
    assert all(isinstance(chunk, DataChunk) for chunk in first.chunks)
    assert all(isinstance(event, Event) for event in first.events)
