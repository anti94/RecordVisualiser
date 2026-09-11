"""Flush ve güvenli dosya kapatma — `F5-029`.

Kabul: **Stop sonrası bütün tam kayıtlar yeniden okunabilir.**

Bu dosyadaki asıl kanıt yazıcının kendi sayaçlarına değil, **üretim
okuyucusuna** dayanır: kapatılan dosya `read_validated_header` ile
doğrulanır ve her kayıt `read_data_record_v2` ile çözülür; CRC alanı
ADR-011'e göre `zlib.crc32` ile bağımsızca yeniden hesaplanıp
karşılaştırılır (yazıcının kendi CRC yardımcısı kullanılmaz, yoksa test
yalnız kodun kendisiyle tutarlı olduğunu söylerdi).

İkinci durum kesinti: bir blok yazılırken disk hata verirse dosyanın
sonunda yarım bir kayıt kalır. Kapatma bunu atmalı ve **ondan önceki tam
kayıtlar** okunabilir kalmalıdır.
"""

from __future__ import annotations

import zlib
from pathlib import Path
from typing import BinaryIO, cast

import pytest

from sonar_analyzer.io.profile_a_format import (
    DATA_RECORD_V1,
    DATA_RECORD_V2,
    FILE_HEADER_V2,
    DataRecordV2,
)
from sonar_analyzer.io.readers.binary_reader import read_data_record_v2
from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.disk_writer import RecordingWriter
from sonar_analyzer.recording.header_writer import build_file_header
from sonar_analyzer.recording.record_writer import build_data_record

START_NS = 1_788_901_200_000_000_000
HEADER_BYTES = FILE_HEADER_V2.size  # 36
RECORD_BYTES = DATA_RECORD_V2.size  # 68


def _record(sequence_no: int) -> bytes:
    """`sequence_no`'ya bağlı, birbirinden ayırt edilebilir değerler taşıyan kayıt."""
    values = [float(sequence_no) + index / 4.0 for index in range(8)]
    return build_data_record(
        sequence_no=sequence_no,
        elapsed_us=sequence_no * 125_000,
        sensor_values=values,
    )


def _expected_values(sequence_no: int) -> list[float]:
    return [float(sequence_no) + index / 4.0 for index in range(8)]


def _read_back(path: Path) -> list[DataRecordV2]:
    """Dosyayı **üretim okuyucusuyla** baştan sona çözer.

    Başlık doğrulanır, ardından kalan baytlar kayıt sınırlarına bölünür.
    Artık bayt kalırsa bu bir hatadır: `F5-029` dosyanın tam bir kayıt
    sınırında bitmesini vaat eder.
    """
    raw = path.read_bytes()
    read_validated_header(raw)
    body = len(raw) - HEADER_BYTES
    assert body % RECORD_BYTES == 0, f"dosya kayit sinirinda bitmiyor: {body} bayt artik"
    return [
        read_data_record_v2(raw, HEADER_BYTES + index * RECORD_BYTES)
        for index in range(body // RECORD_BYTES)
    ]


class _PartialFailureStream:
    """`fail_at`. yazmada bloğun **yarısını** yazıp hata veren akış.

    Disk dolması sırasında gerçekten olabilecek durumu taklit eder: bayt
    bir kısmı diske iner, gerisi inmez.
    """

    def __init__(self, target: BinaryIO, fail_at: int) -> None:
        self._target = target
        self._fail_at = fail_at
        self._writes = 0

    def write(self, data: bytes) -> int:
        self._writes += 1
        if self._writes == self._fail_at:
            self._target.write(data[: len(data) // 2])
            raise OSError(28, "Diskte yer kalmadi")
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()

    def fileno(self) -> int:
        return self._target.fileno()

    def truncate(self, size: int | None = None) -> int:
        return self._target.truncate(size)

    def close(self) -> None:
        self._target.close()


class _NoFilenoStream:
    """`fileno`/`truncate` sunmayan akış — `fsync` yapılamayan durum."""

    def __init__(self, target: BinaryIO) -> None:
        self._target = target

    def write(self, data: bytes) -> int:
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()

    def close(self) -> None:
        self._target.close()


# --------------------------------------------------------------------------- #
# STOP SONRASI BUTUN TAM KAYITLAR YENIDEN OKUNABILIR
# --------------------------------------------------------------------------- #


def test_every_record_is_readable_after_stop(tmp_path: Path) -> None:
    """40 kayıt yazılır, kapatılır ve **hepsi** üretim okuyucusuyla geri gelir."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=256)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(40):
        assert writer.submit(_record(index)) is True
    writer.close()

    records = _read_back(target)
    assert len(records) == 40
    for index, record in enumerate(records):
        assert record.sequence_no == index
        assert record.elapsed_us == index * 125_000
        assert list(record.sensor_values) == _expected_values(index)


def test_the_crc_of_every_reread_record_matches_an_independent_computation(
    tmp_path: Path,
) -> None:
    """ADR-011: CRC kendi alanı hariç hesaplanır; burada `zlib` ile bağımsız doğrulanır."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=64)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(8):
        writer.submit(_record(index))
    writer.close()

    raw = target.read_bytes()
    for index in range(8):
        start = HEADER_BYTES + index * RECORD_BYTES
        body = raw[start : start + DATA_RECORD_V1.size]
        decoded = read_data_record_v2(raw, start)
        assert decoded.record_crc32 == zlib.crc32(body) & 0xFFFF_FFFF


def test_the_file_ends_exactly_on_a_record_boundary(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=64)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(17):
        writer.submit(_record(index))
    writer.close()

    assert target.stat().st_size == HEADER_BYTES + 17 * RECORD_BYTES
    assert writer.committed_bytes == target.stat().st_size
    assert writer.truncated_bytes == 0


def test_records_submitted_right_before_close_are_not_lost(tmp_path: Path) -> None:
    """Kapatmadan hemen önceki gönderimler kuyrukta kalıp kaybolmaz."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=512)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(200):
        writer.submit(_record(index))
    writer.close()  # 200 kaydin cogu hala kuyrukta olabilir

    records = _read_back(target)
    assert len(records) == 200
    assert records[-1].sequence_no == 199


# --------------------------------------------------------------------------- #
# flush(): dosya ACIK kalir, ara nokta diske iner
# --------------------------------------------------------------------------- #


def test_flush_puts_queued_records_on_disk_without_closing(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=64)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    try:
        for index in range(10):
            writer.submit(_record(index))
        assert writer.flush() is True

        assert writer.is_open is True  # dosya hala acik
        assert target.stat().st_size == HEADER_BYTES + 10 * RECORD_BYTES
        assert writer.queue.depth == 0
    finally:
        writer.close()


def test_flushing_twice_is_harmless_and_keeps_recording(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target, queue_maxsize=64)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    try:
        writer.submit(_record(0))
        assert writer.flush() is True
        assert writer.flush() is True
        writer.submit(_record(1))  # kayit devam edebiliyor
        assert writer.flush() is True
    finally:
        writer.close()

    assert len(_read_back(target)) == 2


def test_flushing_a_closed_writer_reports_success(tmp_path: Path) -> None:
    """Kapalı yazıcıda boşaltılacak bir şey yoktur; bu bir hata değildir."""
    writer = RecordingWriter(tmp_path / "kayit.bin")
    assert writer.flush() is True


def test_flush_reports_failure_when_the_disk_errored(tmp_path: Path) -> None:
    """Hata varsa `flush()` "tamam" demez — sessiz başarı yoktur."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(
        target,
        queue_maxsize=64,
        open_stream=lambda path: cast(
            "BinaryIO", _PartialFailureStream(path.open("wb"), fail_at=2)
        ),
    )
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    try:
        writer.submit(_record(0))
        assert writer.flush(timeout_s=1.0) is False
        assert writer.error is not None
    finally:
        writer.close()


# --------------------------------------------------------------------------- #
# YARIM KALAN KAYIT: oncekiler okunabilir kalir
# --------------------------------------------------------------------------- #


def test_an_interrupted_write_does_not_make_earlier_records_unreadable(
    tmp_path: Path,
) -> None:
    """4. blok yarıda kesilir; ilk 3 kayıt tam ve okunabilir kalır."""
    target = tmp_path / "kesik.bin"
    # 1. yazma basliktir (dogrudan), kayit yazmalari 2.'den baslar; 5. yazma
    # = 4. kayit ortasinda kesilir.
    writer = RecordingWriter(
        target,
        queue_maxsize=64,
        open_stream=lambda path: cast(
            "BinaryIO", _PartialFailureStream(path.open("wb"), fail_at=5)
        ),
    )
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(10):
        writer.submit(_record(index))
    writer.close()

    assert writer.error is not None  # hata gizlenmedi
    assert writer.truncated_bytes == RECORD_BYTES // 2  # atilan yarim blok gorunur

    records = _read_back(target)  # artik bayt kalmadigini da dogrular
    assert len(records) == 3
    assert [record.sequence_no for record in records] == [0, 1, 2]
    assert list(records[2].sensor_values) == _expected_values(2)


def test_the_safe_length_excludes_the_interrupted_block(tmp_path: Path) -> None:
    target = tmp_path / "kesik.bin"
    writer = RecordingWriter(
        target,
        queue_maxsize=64,
        open_stream=lambda path: cast(
            "BinaryIO", _PartialFailureStream(path.open("wb"), fail_at=3)
        ),
    )
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(5):
        writer.submit(_record(index))
    writer.close()

    assert writer.committed_bytes == HEADER_BYTES + RECORD_BYTES
    assert target.stat().st_size == writer.committed_bytes
    assert writer.written_records == 1


def test_a_header_only_recording_stays_readable(tmp_path: Path) -> None:
    """Hiç kayıt yazılmadan durdurulan dosya da geçerli bir başlık taşır."""
    target = tmp_path / "bos.bin"
    writer = RecordingWriter(target)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    writer.close()

    assert _read_back(target) == []
    assert target.stat().st_size == HEADER_BYTES


# --------------------------------------------------------------------------- #
# kapatma dayanikliligi
# --------------------------------------------------------------------------- #


def test_closing_twice_is_harmless(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    writer.submit(_record(0))
    writer.close()
    writer.close()  # ikinci cagri patlamamali

    assert writer.is_open is False
    assert len(_read_back(target)) == 1


def test_a_stream_without_fileno_still_closes_cleanly(tmp_path: Path) -> None:
    """`fsync` yapılamayan akışta kapatma yine de tam kayıt bırakır."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(
        target,
        open_stream=lambda path: cast("BinaryIO", _NoFilenoStream(path.open("wb"))),
    )
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    for index in range(3):
        writer.submit(_record(index))
    writer.close()

    assert writer.truncated_bytes == 0
    assert len(_read_back(target)) == 3


def test_reopening_a_closed_writer_is_refused_rather_than_half_working(
    tmp_path: Path,
) -> None:
    """Kapanan yazıcının kuyruğu da kapanmıştır; sessizce boş dosya yazmaz."""
    target = tmp_path / "kayit.bin"
    writer = RecordingWriter(target)
    writer.open(build_file_header(start_time_utc_ns=START_NS))
    writer.submit(_record(0))
    writer.close()

    with pytest.raises(RuntimeError, match="Kapatilan kayit yeniden acilamaz"):
        writer.open(build_file_header(start_time_utc_ns=START_NS))
    assert len(_read_back(target)) == 1  # ilk dosya bozulmadi
