"""Replay zamanlaması ve durdurma — `F5-004`.

Kabul: pause/stop sonrası beklenmeyen paket yayınlanmaz.

`F5-003` `pause()`/`resume()`/`stop()`'u ekledi ve temel bir "duraklatma en
az bir engelleme turu üretir" testiyle bıraktı. Bu dosya iddiayı sıkılaştırır:
duraklatmanın **süresiz** engellediğini (bir zaman aşımı değil, gerçek bir
kilit olduğunu), devam etmenin konumu **korduğunu** (sıfırlamadığını),
durdurmanın duraklatmadan da çağrılabildiğini ve ara ara duraklat/devam
etmenin hiçbir pencereyi atlamadığını/tekrarlamadığını kanıtlar.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.repository.mock_repository import MockRecordingRepository


def _repository(duration_s: float = 1.0) -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=duration_s)


def _snapshot(packet: LivePacket) -> tuple[object, ...]:
    chunks = tuple(
        (chunk.channel_id, chunk.timestamps_ns.tolist(), chunk.values.tolist())
        for chunk in packet.chunks
    )
    events = tuple((event.timestamp_ns, event.source, event.code) for event in packet.events)
    return (packet.sequence_no, chunks, events)


class _NoProgress(Exception):
    """`_PauseGuard` sinyali: kontrol duraklatma döngüsünden çıkmadı."""


def _no_delay(_seconds: float) -> None:
    """Gerçekten uyumaz — bu dosyadaki testler süre değil sayım/sıra doğrular."""


# --------------------------------------------------------------------------- #
# duraklatma gercekten sinirsiz engeller
# --------------------------------------------------------------------------- #


def test_pause_blocks_indefinitely_not_just_once() -> None:
    """Hiç `resume()` çağrılmazsa döngü 50 turdan sonra bile paket üretmemeli."""
    calls = 0

    def guard_sleep(_seconds: float) -> None:
        nonlocal calls
        calls += 1
        if calls > 50:
            raise _NoProgress

    source = FileReplaySource(_repository(), sleep=guard_sleep)
    source.connect()
    source.pause()
    with pytest.raises(_NoProgress):
        next(iter(source.packets()))
    assert calls == 51  # kontrol hicbir zaman paket uretme koduna ulasmadi


def test_resume_continues_from_the_next_window_not_from_the_start() -> None:
    """Duraklatıp devam etmek `sequence_no`'yu sıfırlamaz — konum korunur."""

    def auto_resuming_sleep(_seconds: float) -> None:
        source.resume()  # duraklatilmissa iptal eder; degilse etkisiz (idempotent)

    source = FileReplaySource(_repository(duration_s=1.0), sleep=auto_resuming_sleep)
    source.connect()
    iterator = source.packets()
    assert next(iterator).sequence_no == 0
    assert next(iterator).sequence_no == 1

    source.pause()
    third = next(iterator)  # duraklat -> bir tur uyku (auto-resume) -> devam
    assert third.sequence_no == 2  # 0'a degil, 2'ye devam etti


# --------------------------------------------------------------------------- #
# durdurma
# --------------------------------------------------------------------------- #


def test_stop_mid_stream_yields_no_further_packet_and_exact_count_before() -> None:
    source = FileReplaySource(_repository(duration_s=1.0), sleep=_no_delay)
    source.connect()
    collected: list[LivePacket] = []
    for packet in source.packets():
        collected.append(packet)
        if packet.sequence_no == 2:
            source.stop()

    assert [p.sequence_no for p in collected] == [0, 1, 2]  # tam olarak durdurulana kadar


def test_stop_called_while_paused_ends_the_generator_without_resume() -> None:
    """Duraklatmışken `stop()` çağrılırsa `resume()` beklemeden üretici biter."""
    calls = 0

    def sleep_then_stop_on_third_call(_seconds: float) -> None:
        nonlocal calls
        calls += 1
        if calls >= 3:
            source.stop()

    source = FileReplaySource(_repository(duration_s=1.0), sleep=sleep_then_stop_on_third_call)
    source.connect()
    source.pause()
    with pytest.raises(StopIteration):
        next(iter(source.packets()))
    assert calls == 3  # resume() hic cagrilmadan, tam 3 turda durdu


def test_a_stopped_generator_can_be_restarted_from_zero() -> None:
    source = FileReplaySource(_repository(duration_s=1.0), sleep=_no_delay)
    source.connect()
    iterator = source.packets()
    assert next(iterator).sequence_no == 0
    assert next(iterator).sequence_no == 1
    source.stop()
    with pytest.raises(StopIteration):
        next(iterator)

    restarted = list(source.packets())
    assert [p.sequence_no for p in restarted] == list(range(8))  # tam kayit, en bastan


# --------------------------------------------------------------------------- #
# ara ara duraklatma icerigi bozmaz
# --------------------------------------------------------------------------- #


def test_pausing_between_windows_never_skips_or_duplicates_content() -> None:
    repository = _repository(duration_s=1.0)  # 8 pencere
    reference = FileReplaySource(repository, sleep=_no_delay)
    reference.connect()
    baseline = [_snapshot(packet) for packet in reference.packets()]

    pause_extra_calls = 0

    def auto_resuming_sleep(_seconds: float) -> None:
        nonlocal pause_extra_calls
        pause_extra_calls += 1
        source.resume()  # duraklatilmissa iptal eder; degilse etkisiz (idempotent)

    source = FileReplaySource(repository, sleep=auto_resuming_sleep)
    source.connect()
    collected: list[tuple[object, ...]] = []
    for packet in source.packets():
        collected.append(_snapshot(packet))
        if packet.sequence_no in (1, 4):
            source.pause()

    assert collected == baseline
    # 8 pencere pacing uykusu + iki duraklatma olayinin her biri icin
    # bir ek "kilidi acan" uyku turu.
    assert pause_extra_calls == 8 + 2
