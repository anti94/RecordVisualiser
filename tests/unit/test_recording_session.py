"""Disk dolması ve yazma hatası işleme — `F5-030`.

Kabul: **Kayıt hata durumuna geçer; başarılı kayıt mesajı verilmez.**

İki yarı ayrı ayrı kanıtlanır:

* *Hata durumuna geçer*: gerçek bir `OSError(ENOSPC)` yazma sırasında
  fırlatılır ve oturumun `RecordingState.FAILED`'e geçtiği, `stop()`
  sonucunun `succeeded=False` olduğu gösterilir.
* *Başarılı mesaj verilmez*: sonuç metninde "tamamlandi" geçmediği ve
  bunun yerine sorunu adıyla anan bir cümle kurulduğu doğrulanır. Bu,
  hata bayrağı doğru ama kullanıcıya hâlâ "kayıt alındı" diyen bir
  arayüz ihtimalini kapatır.

Hata sonrası dosyanın okunabilirliği de burada bir kez daha üretim
okuyucusuyla doğrulanır — `F5-029` ile birlikte anlamlı olan şey budur:
kayıt başarısız, ama kurtulan kayıtlar sağlam.
"""

from __future__ import annotations

import errno
import time
from pathlib import Path
from typing import BinaryIO, cast

import pytest

from sonar_analyzer.io.profile_a_format import DATA_RECORD_V2, FILE_HEADER_V2
from sonar_analyzer.io.readers.binary_reader import read_data_record_v2
from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.disk_writer import RecordingWriter
from sonar_analyzer.recording.header_writer import build_file_header
from sonar_analyzer.recording.record_writer import build_data_record
from sonar_analyzer.recording.session import (
    RecordingSession,
    RecordingStartError,
    RecordingState,
)

START_NS = 1_788_901_200_000_000_000
HEADER_BYTES = FILE_HEADER_V2.size
RECORD_BYTES = DATA_RECORD_V2.size
PLENTY = 1 << 40  # 1 TiB bos alan


def _header() -> bytes:
    return build_file_header(start_time_utc_ns=START_NS)


def _record(sequence_no: int) -> bytes:
    return build_data_record(
        sequence_no=sequence_no,
        elapsed_us=sequence_no * 125_000,
        sensor_values=[float(sequence_no)] * 8,
    )


class _FailingStream:
    """`fail_at`. yazmada verilen `errno` ile patlayan akış."""

    def __init__(self, target: BinaryIO, fail_at: int, code: int) -> None:
        self._target = target
        self._fail_at = fail_at
        self._code = code
        self._writes = 0

    def write(self, data: bytes) -> int:
        self._writes += 1
        if self._writes >= self._fail_at:
            raise OSError(self._code, "Simule edilen disk hatasi")
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()

    def fileno(self) -> int:
        return self._target.fileno()

    def truncate(self, size: int | None = None) -> int:
        return self._target.truncate(size)

    def close(self) -> None:
        self._target.close()


class _SlowStream:
    """Her yazmada gerçekten bekleyen akış — yavaş diski taklit eder."""

    def __init__(self, target: BinaryIO, delay_s: float) -> None:
        self._target = target
        self._delay_s = delay_s

    def write(self, data: bytes) -> int:
        time.sleep(self._delay_s)
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()

    def fileno(self) -> int:
        return self._target.fileno()

    def truncate(self, size: int | None = None) -> int:
        return self._target.truncate(size)

    def close(self) -> None:
        self._target.close()


def _failing_session(
    path: Path,
    *,
    fail_at: int,
    code: int = errno.ENOSPC,
    free: int = PLENTY,
) -> RecordingSession:
    def factory(target: Path) -> RecordingWriter:
        return RecordingWriter(
            target,
            queue_maxsize=256,
            open_stream=lambda p: cast("BinaryIO", _FailingStream(p.open("wb"), fail_at, code)),
        )

    return RecordingSession(path, writer_factory=factory, free_space=lambda _p: free)


def _healthy_session(path: Path, *, free: int = PLENTY) -> RecordingSession:
    return RecordingSession(path, free_space=lambda _p: free)


def _wait_for_failure(session: RecordingSession, *, timeout_s: float = 5.0) -> RecordingState:
    """Worker'ın hatayı görmesini bekler.

    Yazma ayrı bir thread'de olduğu için hata `write()` döndükten hemen
    sonra görünmez; sıkı bir döngüyle yoklamak yalnızca zamanlamayı test
    ederdi.
    """
    deadline = time.monotonic() + timeout_s
    while session.poll() is RecordingState.RECORDING and time.monotonic() < deadline:
        time.sleep(0.005)
    return session.state


def _drain(session: RecordingSession, count: int) -> None:
    """Hata görülene kadar kayıt gönderir; hata sonrası göndermeyi bırakır."""
    for index in range(count):
        if session.poll() is not RecordingState.RECORDING:
            return
        session.write(_record(index))


# --------------------------------------------------------------------------- #
# KAYIT HATA DURUMUNA GECER
# --------------------------------------------------------------------------- #


def test_a_disk_full_write_puts_the_session_into_the_failed_state(tmp_path: Path) -> None:
    session = _failing_session(tmp_path / "kayit.bin", fail_at=4)  # 1=baslik, 4. yazma patlar
    session.start(_header())
    _drain(session, 20)
    outcome = session.stop()

    assert session.state is RecordingState.FAILED
    assert outcome.state is RecordingState.FAILED
    assert outcome.succeeded is False


def test_the_disk_full_case_is_named_rather_than_reported_generically(tmp_path: Path) -> None:
    session = _failing_session(tmp_path / "kayit.bin", fail_at=2, code=errno.ENOSPC)
    session.start(_header())
    _drain(session, 5)
    outcome = session.stop()

    assert "Diskte yer kalmadi" in outcome.message


def test_a_permission_error_gets_its_own_message(tmp_path: Path) -> None:
    session = _failing_session(tmp_path / "kayit.bin", fail_at=2, code=errno.EACCES)
    session.start(_header())
    _drain(session, 5)
    outcome = session.stop()

    assert "yazma izni yok" in outcome.message
    assert "Diskte yer kalmadi" not in outcome.message


def test_an_unexpected_io_error_still_fails_the_session(tmp_path: Path) -> None:
    session = _failing_session(tmp_path / "kayit.bin", fail_at=2, code=errno.EIO)
    session.start(_header())
    _drain(session, 5)
    outcome = session.stop()

    assert outcome.succeeded is False
    assert "Diske yazilamadi" in outcome.message


def test_polling_notices_the_error_without_any_further_write(tmp_path: Path) -> None:
    """Akış sessizleşse bile disk hatası görülür — yoksa fark edilmezdi."""
    session = _failing_session(tmp_path / "kayit.bin", fail_at=2)
    session.start(_header())
    session.write(_record(0))

    # Bundan sonra hic write() cagrilmaz; yalniz poll() ile fark edilmeli.
    assert _wait_for_failure(session) is RecordingState.FAILED


def test_writing_after_a_failure_is_refused_not_silently_accepted(tmp_path: Path) -> None:
    session = _failing_session(tmp_path / "kayit.bin", fail_at=2)
    session.start(_header())
    _drain(session, 10)

    assert _wait_for_failure(session) is RecordingState.FAILED
    with pytest.raises(RuntimeError, match="Kayit suruyor degil: failed"):
        session.write(_record(99))


# --------------------------------------------------------------------------- #
# BASARILI KAYIT MESAJI VERILMEZ
# --------------------------------------------------------------------------- #


def test_a_failed_session_never_says_the_recording_completed(tmp_path: Path) -> None:
    session = _failing_session(tmp_path / "kayit.bin", fail_at=6)
    session.start(_header())
    _drain(session, 50)
    outcome = session.stop()

    assert "tamamlandi" not in outcome.message.lower()
    assert outcome.succeeded is False


def test_a_failure_after_many_good_records_is_still_a_failure(tmp_path: Path) -> None:
    """Çok sayıda kayıt yazılmış olması sonucu "başarılı" yapmaz."""
    session = _failing_session(tmp_path / "kayit.bin", fail_at=40)
    session.start(_header())
    _drain(session, 100)
    outcome = session.stop()

    assert outcome.record_count >= 30  # cogu kayit yazildi
    assert outcome.succeeded is False
    assert "tamamlandi" not in outcome.message.lower()


def test_the_failure_message_says_how_much_was_saved(tmp_path: Path) -> None:
    session = _failing_session(tmp_path / "kayit.bin", fail_at=10)
    session.start(_header())
    _drain(session, 50)
    outcome = session.stop()

    assert f"{outcome.record_count} tam kayit" in outcome.message
    assert str(session.path) in outcome.message


def test_the_records_written_before_the_failure_are_still_readable(tmp_path: Path) -> None:
    """Kayıt başarısız; ama kurtulan kayıtlar üretim okuyucusuyla açılabilir."""
    target = tmp_path / "kayit.bin"
    session = _failing_session(target, fail_at=12)
    session.start(_header())
    _drain(session, 60)
    outcome = session.stop()

    raw = target.read_bytes()
    read_validated_header(raw)
    body = len(raw) - HEADER_BYTES
    assert body % RECORD_BYTES == 0  # yarim kayit kalmadi (F5-029)
    assert body // RECORD_BYTES == outcome.record_count
    for index in range(outcome.record_count):
        decoded = read_data_record_v2(raw, HEADER_BYTES + index * RECORD_BYTES)
        assert decoded.sequence_no == index


def test_the_recording_file_is_not_deleted_after_a_failure(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    session = _failing_session(target, fail_at=8)
    session.start(_header())
    _drain(session, 30)
    session.stop()

    assert target.exists()  # elde olan veri, olmayandan iyidir


# --------------------------------------------------------------------------- #
# DISK DOLMASI: kayda hic baslanmaz
# --------------------------------------------------------------------------- #


def test_recording_does_not_start_when_the_disk_is_almost_full(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    session = RecordingSession(target, free_space=lambda _p: 1024, min_free_bytes=1 << 20)

    with pytest.raises(RecordingStartError, match="Diskte yeterli yer yok"):
        session.start(_header())

    assert session.state is RecordingState.FAILED
    assert target.exists() is False  # olmeye mahkum bir dosya yaratilmadi


def test_the_refusal_names_the_free_and_the_required_amount(tmp_path: Path) -> None:
    session = RecordingSession(
        tmp_path / "kayit.bin", free_space=lambda _p: 4096, min_free_bytes=8192
    )
    with pytest.raises(RecordingStartError) as excinfo:
        session.start(_header())

    assert "4096" in str(excinfo.value)
    assert "8192" in str(excinfo.value)


def test_stopping_a_session_that_never_started_does_not_claim_success(tmp_path: Path) -> None:
    session = RecordingSession(tmp_path / "kayit.bin", free_space=lambda _p: 0)
    with pytest.raises(RecordingStartError):
        session.start(_header())
    outcome = session.stop()

    assert outcome.succeeded is False
    assert outcome.record_count == 0
    assert "tamamlandi" not in outcome.message.lower()


def test_a_recording_starts_when_there_is_room(tmp_path: Path) -> None:
    session = _healthy_session(tmp_path / "kayit.bin")
    session.start(_header())
    try:
        assert session.state is RecordingState.RECORDING
        assert session.is_recording is True
    finally:
        session.stop()


def test_an_unopenable_path_fails_the_session_instead_of_pretending(tmp_path: Path) -> None:
    """Dosya açılamazsa kayıt başlamış gibi yapılmaz."""
    blocker = tmp_path / "engel"
    blocker.write_bytes(b"x")

    def factory(target: Path) -> RecordingWriter:
        return RecordingWriter(target)

    # 'engel' bir dosya; altinda dosya acmak OSError verir.
    session = RecordingSession(
        blocker / "kayit.bin", writer_factory=factory, free_space=lambda _p: PLENTY
    )
    with pytest.raises(RecordingStartError, match="Kayit dosyasi acilamadi"):
        session.start(_header())

    assert session.state is RecordingState.FAILED


# --------------------------------------------------------------------------- #
# temiz kosu: basari mesaji YALNIZ burada
# --------------------------------------------------------------------------- #


def test_a_clean_run_reports_success(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    session = _healthy_session(target)
    session.start(_header())
    for index in range(25):
        session.write(_record(index))
    outcome = session.stop()

    assert outcome.state is RecordingState.STOPPED
    assert outcome.succeeded is True
    assert outcome.record_count == 25
    assert "Kayit tamamlandi" in outcome.message
    assert outcome.error is None


def test_a_clean_run_leaves_a_fully_readable_file(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    session = _healthy_session(target)
    session.start(_header())
    for index in range(25):
        session.write(_record(index))
    session.stop()

    raw = target.read_bytes()
    read_validated_header(raw)
    assert len(raw) == HEADER_BYTES + 25 * RECORD_BYTES


def test_drops_are_disclosed_even_on_a_successful_run(tmp_path: Path) -> None:
    """Tamamlandı ama eksik: düşen kayıtlar mesajda saklanmaz."""
    target = tmp_path / "kayit.bin"

    def factory(path: Path) -> RecordingWriter:
        # Yavas disk + tek blokluk kuyruk: dusme garanti, kosula bagli degil.
        return RecordingWriter(
            path,
            queue_maxsize=1,
            open_stream=lambda p: cast("BinaryIO", _SlowStream(p.open("wb"), 0.01)),
        )

    session = RecordingSession(target, writer_factory=factory, free_space=lambda _p: PLENTY)
    session.start(_header())
    for index in range(60):
        session.write(_record(index))
    outcome = session.stop()

    assert outcome.succeeded is True
    assert outcome.dropped_records > 0
    assert f"{outcome.dropped_records} kayit dustu" in outcome.message
    assert outcome.dropped_records == session.dropped_records


def test_starting_twice_while_recording_is_refused(tmp_path: Path) -> None:
    session = _healthy_session(tmp_path / "kayit.bin")
    session.start(_header())
    try:
        with pytest.raises(RuntimeError, match="Kayit zaten suruyor"):
            session.start(_header())
    finally:
        session.stop()


def test_the_session_reports_its_counters_while_recording(tmp_path: Path) -> None:
    session = _healthy_session(tmp_path / "kayit.bin")
    session.start(_header())
    try:
        for index in range(5):
            session.write(_record(index))
        assert session.poll() is RecordingState.RECORDING
        assert session.dropped_records == 0
    finally:
        outcome = session.stop()
    assert session.record_count == outcome.record_count == 5
