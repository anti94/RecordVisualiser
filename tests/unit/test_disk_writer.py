"""Disk yazma kuyruğu ve worker — `F5-028`.

Kabul: **yavaş disk UI'ı kilitlemez; taşma ve kayıp görünürdür.**

Birinci yarı ölçülerek kanıtlanır: yazma akışı kasıtlı yavaşlatılır
(blok başına gerçek gecikme) ve üreticinin `submit()` çağrısının o
gecikmeden **bağımsız** olarak hızlı döndüğü ölçülür.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, cast

import pytest

from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.disk_writer import (
    DiskWriteQueue,
    RecordingWriter,
)
from sonar_analyzer.recording.header_writer import build_file_header
from sonar_analyzer.recording.record_writer import build_data_record

START_NS = 1_788_901_200_000_000_000
VALUES = (0.0,) * 8


def _record(sequence_no: int) -> bytes:
    return build_data_record(
        sequence_no=sequence_no,
        elapsed_us=sequence_no * 125_000,
        sensor_values=VALUES,
    )


class _SlowStream:
    """Her yazmada **gerçekten** bekleyen akış — yavaş diski taklit eder."""

    def __init__(self, target: BinaryIO, delay_s: float) -> None:
        self._target = target
        self._delay_s = delay_s

    def write(self, data: bytes) -> int:
        time.sleep(self._delay_s)
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()

    def close(self) -> None:
        self._target.close()


def _slow_opener(delay_s: float) -> Callable[[Path], BinaryIO]:
    """`RecordingWriter`'a enjekte edilen yavaş disk açıcısı."""

    def opener(path: Path) -> BinaryIO:
        return cast("BinaryIO", _SlowStream(path.open("wb"), delay_s))

    return opener


# --------------------------------------------------------------------------- #
# kuyruk: tasma GORUNUR, gonderim BEKLEMEZ
# --------------------------------------------------------------------------- #


def test_a_full_queue_drops_and_counts_without_blocking() -> None:
    queue = DiskWriteQueue(maxsize=3)
    accepted = [queue.submit(_record(index)) for index in range(10)]

    assert accepted[:3] == [True, True, True]
    assert accepted[3:] == [False] * 7
    assert queue.depth == 3  # sinir asilmadi
    assert queue.dropped_records == 7  # kayip gorunur
    assert queue.accepted_records == 3


def test_the_queue_depth_never_exceeds_its_limit() -> None:
    queue = DiskWriteQueue(maxsize=5)
    for index in range(500):
        queue.submit(_record(index))
        assert queue.depth <= 5
    assert queue.peak_depth == 5


def test_taking_frees_room_for_new_blocks() -> None:
    queue = DiskWriteQueue(maxsize=2)
    queue.submit(_record(0))
    queue.submit(_record(1))
    assert queue.submit(_record(2)) is False

    assert queue.take() is not None
    assert queue.submit(_record(3)) is True


def test_blocks_come_back_in_order() -> None:
    queue = DiskWriteQueue(maxsize=4)
    for index in range(3):
        queue.submit(_record(index))

    taken = [queue.take() for _ in range(3)]
    assert taken == [_record(0), _record(1), _record(2)]


def test_an_empty_queue_returns_none() -> None:
    assert DiskWriteQueue(maxsize=2).take() is None


def test_a_closed_queue_refuses_new_blocks() -> None:
    queue = DiskWriteQueue(maxsize=2)
    queue.close()
    with pytest.raises(RuntimeError, match="Kuyruk kapatildi"):
        queue.submit(_record(0))


def test_maxsize_must_be_positive() -> None:
    with pytest.raises(ValueError, match="maxsize pozitif olmali"):
        DiskWriteQueue(maxsize=0)


# --------------------------------------------------------------------------- #
# YAVAS DISK UI'YI KILITLEMEZ
# --------------------------------------------------------------------------- #


def test_submitting_is_fast_even_when_the_disk_is_slow(tmp_path: Path) -> None:
    """Disk blok başına 50 ms harcarken üretici mikrosaniyelerde döner."""
    target = tmp_path / "yavas.bin"
    writer = RecordingWriter(target, queue_maxsize=64, open_stream=_slow_opener(0.05))
    writer.open(build_file_header(start_time_utc_ns=START_NS))

    try:
        durations: list[float] = []
        for index in range(20):
            started = time.perf_counter()
            writer.submit(_record(index))
            durations.append(time.perf_counter() - started)
    finally:
        writer.close()

    # Disk blok basina 50 ms harciyor; gonderim bunun yuzde birinden hizli.
    assert max(durations) < 0.0005, f"en yavas gonderim {max(durations):.6f} s"


def test_a_slow_disk_causes_visible_drops_rather_than_a_stall(tmp_path: Path) -> None:
    """Yavaş disk + küçük kuyruk: üretici durmaz, kayıp sayaçta görünür."""
    target = tmp_path / "tasma.bin"
    writer = RecordingWriter(target, queue_maxsize=4, open_stream=_slow_opener(0.02))
    writer.open(build_file_header(start_time_utc_ns=START_NS))

    try:
        for index in range(200):
            writer.submit(_record(index))
        dropped = writer.dropped_records
    finally:
        writer.close()

    assert dropped > 0  # tasma oldu
    assert writer.queue.peak_depth <= 4  # sinir asilmadi


# --------------------------------------------------------------------------- #
# gercek dosyaya yazim
# --------------------------------------------------------------------------- #


def test_the_header_is_written_directly_not_through_the_queue(tmp_path: Path) -> None:
    """Başlık kuyruk taşmasından etkilenmez; dosyanın ilk baytı olmalı."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=1)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    writer.close()

    header = read_validated_header(target.read_bytes())
    assert header.start_time_utc_ns == START_NS


def test_submitted_records_reach_the_file(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    header = build_file_header(start_time_utc_ns=START_NS)
    writer = RecordingWriter(target, queue_maxsize=64)
    writer.open(header)
    try:
        for index in range(10):
            assert writer.submit(_record(index)) is True
    finally:
        writer.close()

    raw = target.read_bytes()
    assert len(raw) == len(header) + 10 * len(_record(0))
    assert writer.written_records == 10
    assert writer.dropped_records == 0


def test_closing_flushes_what_is_still_queued(tmp_path: Path) -> None:
    """Kapatma sırasında kuyrukta kalan bloklar sessizce kaybolmaz."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=256)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(50):
        writer.submit(_record(index))
    writer.close()

    assert writer.written_records == 50
    assert target.stat().st_size == 36 + 50 * 68  # v2 basligi + 50 v2 kaydi


def test_submitting_before_open_is_refused(tmp_path: Path) -> None:
    writer = RecordingWriter(tmp_path / "kayit.bin")
    with pytest.raises(RuntimeError, match="Once open\\(\\) cagrilmali"):
        writer.submit(_record(0))


def test_opening_twice_is_refused(tmp_path: Path) -> None:
    writer = RecordingWriter(tmp_path / "kayit.bin")
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    try:
        with pytest.raises(RuntimeError, match="Kayit zaten acik"):
            writer.open(build_file_header(start_time_utc_ns=START_NS))
    finally:
        writer.close()


def test_a_missing_directory_is_created(tmp_path: Path) -> None:
    target = tmp_path / "yeni" / "klasor" / "kayit.bin"
    writer = RecordingWriter(target)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    writer.close()
    assert target.exists()


def test_the_writer_reports_no_error_on_a_clean_run(tmp_path: Path) -> None:
    writer = RecordingWriter(tmp_path / "kayit.bin")
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    writer.submit(_record(0))
    writer.close()
    assert writer.error is None
