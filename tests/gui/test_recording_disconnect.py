"""Bağlantı kesilmesinde kayıt davranışı — `F5-033`.

Kabul: **Tam kayıtlar korunur; boşluk ve kapanış nedeni loglanır.**

Üç şey ayrı ayrı kanıtlanır:

* *Tam kayıtlar korunur* — kopma anında yazılmış olan her kayıt, üretim
  okuyucusuyla (`read_validated_header` + `read_data_record_v2`) tek tek
  geri okunur ve dosyanın tam bir kayıt sınırında bittiği doğrulanır.
* *Boşluk loglanır* — akışta kasten atlanan pencereler, log'da **doğru
  aralık ve sayıyla** görünür. Aralık mutlak zaman ızgarasından gelir,
  dosya içi sıra numarasından değil; dosya değişse bile boşluk kaybolmaz.
* *Kapanış nedeni loglanır* — "kullanıcı durdurdu" ile "bağlantı kesildi"
  diskte birbirinin aynı olduğu için neden ayrıca yazılır.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.io.profile_a_format import DATA_RECORD_V2, FILE_HEADER_V2
from sonar_analyzer.io.readers.binary_reader import read_data_record_v2
from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.rotation import ClosureReason, RotationPolicy
from sonar_analyzer.ui.main_window import MainWindow

START_NS = 1_788_901_200_000_000_000
HEADER_BYTES = FILE_HEADER_V2.size
RECORD_BYTES = DATA_RECORD_V2.size
CHANNELS = tuple(
    ChannelMetadata(id=f"ch{index}", path=f"/ch{index}", name=f"Kanal {index}", dtype="float32")
    for index in range(8)
)


def _packet(window: int) -> LivePacket:
    at_ns = START_NS + window * RECORD_PERIOD_NS
    chunks = [
        DataChunk(
            channel.id,
            np.array([at_ns], dtype=np.int64),
            np.array([float(window)], dtype=np.float64),
        )
        for channel in CHANNELS
    ]
    return LivePacket(sequence_no=window, received_ns=at_ns, chunks=chunks)


class _WindowSource:
    """Verilen pencere listesini üreten kaynak; liste bitince akış biter."""

    def __init__(self, windows: list[int], *, fail_with: str | None = None) -> None:
        self._windows = windows
        self._fail_with = fail_with
        self.state = ConnectionState.CONNECTED
        self._stats = LiveStats()

    def channels(self) -> tuple[ChannelMetadata, ...]:
        return CHANNELS

    def stats(self) -> LiveStats:
        return self._stats

    def connect(self) -> None:
        self.state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self.state = ConnectionState.DISCONNECTED

    def packets(self) -> Iterator[LivePacket]:
        for window in self._windows:
            yield _packet(window)
        if self._fail_with is not None:
            # Kaynagin cokmesi: worker bunu `failed` sinyaline cevirir.
            raise ConnectionResetError(self._fail_with)


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def _stream(win: MainWindow, source: _WindowSource, tmp_path: Path, expected: int) -> None:
    """Kaynağı takar, kaydı başlatır ve beklenen paket sayısını pompalar."""
    win.set_live_source(source)
    win.start_live_stream()
    win.start_recording(tmp_path, policy=RotationPolicy(max_bytes=1 << 30))
    pumped = 0
    for _ in range(3000):
        pumped += win.pump_live_stream(limit=8)
        if pumped >= expected:
            return
        win.thread().msleep(1)
    raise AssertionError(f"yalniz {pumped}/{expected} paket pompalandi")


def _log(win: MainWindow) -> str:
    return "\n".join(win.bottom_dock.log_lines())


def _records(path: Path) -> list[int]:
    """Dosyadaki kayıtların sıra numaraları — üretim okuyucusuyla."""
    raw = path.read_bytes()
    read_validated_header(raw)
    body = len(raw) - HEADER_BYTES
    assert body % RECORD_BYTES == 0, f"dosya kayit sinirinda bitmiyor: {body}"
    return [
        read_data_record_v2(raw, HEADER_BYTES + index * RECORD_BYTES).sequence_no
        for index in range(body // RECORD_BYTES)
    ]


# --------------------------------------------------------------------------- #
# TAM KAYITLAR KORUNUR
# --------------------------------------------------------------------------- #


def test_every_record_written_before_the_drop_survives(win: MainWindow, tmp_path: Path) -> None:
    """Kaynak çöktüğünde o ana kadarki kayıtların hepsi okunabilir kalır."""
    source = _WindowSource(list(range(12)), fail_with="baglanti dustu")
    _stream(win, source, tmp_path, expected=12)
    win.stop_recording(ClosureReason.DISCONNECTED)
    win.stop_live_stream()

    written = next(iter(tmp_path.glob("*.bin")))
    assert _records(written) == list(range(12))


def test_the_file_ends_on_a_record_boundary_after_a_drop(win: MainWindow, tmp_path: Path) -> None:
    source = _WindowSource(list(range(9)), fail_with="kopma")
    _stream(win, source, tmp_path, expected=9)
    win.stop_recording(ClosureReason.DISCONNECTED)
    win.stop_live_stream()

    written = next(iter(tmp_path.glob("*.bin")))
    assert written.stat().st_size == HEADER_BYTES + 9 * RECORD_BYTES


def test_disconnecting_closes_the_recording_and_keeps_the_records(
    win: MainWindow, tmp_path: Path
) -> None:
    """`Disconnect` kaydı kapatır; yazılanlar korunur."""
    source = _WindowSource(list(range(10)))
    _stream(win, source, tmp_path, expected=10)
    win.disconnect_live_source()
    win.stop_live_stream()

    assert win.recording_active is False
    written = next(iter(tmp_path.glob("*.bin")))
    assert _records(written) == list(range(10))


# --------------------------------------------------------------------------- #
# KAPANIS NEDENI LOGLANIR
# --------------------------------------------------------------------------- #


def test_a_disconnect_is_logged_as_the_closure_reason(win: MainWindow, tmp_path: Path) -> None:
    source = _WindowSource(list(range(6)))
    _stream(win, source, tmp_path, expected=6)
    win.disconnect_live_source()
    win.stop_live_stream()

    assert "Kayit kapandi (baglanti kesildi)." in _log(win)


def test_a_user_stop_is_logged_as_a_user_stop(win: MainWindow, tmp_path: Path) -> None:
    """Aynı dosya, farklı neden: ikisi karışmamalı."""
    source = _WindowSource(list(range(6)))
    _stream(win, source, tmp_path, expected=6)
    win.stop_recording()
    win.stop_live_stream()

    log = _log(win)
    assert "Kayit kapandi (kullanici durdurdu)." in log
    assert "baglanti kesildi" not in log


def test_a_source_error_closes_the_recording_with_its_own_reason(
    win: MainWindow, tmp_path: Path, qtbot: QtBot
) -> None:
    """Kaynak çökerse kayıt açık bırakılmaz; neden "kaynak hatası" olur."""
    source = _WindowSource(list(range(5)), fail_with="soket coktu")
    _stream(win, source, tmp_path, expected=5)
    qtbot.waitUntil(lambda: win.recording_active is False, timeout=5000)
    win.stop_live_stream()

    log = _log(win)
    assert "Canli okuma hatasi" in log
    assert "Kayit kapandi (kaynak hatasi)." in log


def test_the_recorder_remembers_the_first_reason(win: MainWindow, tmp_path: Path) -> None:
    """İlk kapanış nedeni korunur; sonraki `stop()` onu ezmez."""
    source = _WindowSource(list(range(4)))
    win.set_live_source(source)
    win.start_live_stream()
    recorder = win.start_recording(tmp_path)
    win.pump_live_stream(limit=8)
    win.stop_recording(ClosureReason.DISCONNECTED)
    win.stop_recording(ClosureReason.USER_STOP)  # etkisiz: kayit zaten kapali
    win.stop_live_stream()

    assert recorder.closure_reason is ClosureReason.DISCONNECTED


# --------------------------------------------------------------------------- #
# BOSLUK LOGLANIR
# --------------------------------------------------------------------------- #


def test_a_gap_in_the_stream_is_logged_with_its_range(win: MainWindow, tmp_path: Path) -> None:
    """3..6 arası hiç gelmezse log bunu aralık ve sayıyla söyler."""
    source = _WindowSource([0, 1, 2, 7, 8, 9])
    _stream(win, source, tmp_path, expected=6)
    win.stop_recording(ClosureReason.DISCONNECTED)
    win.stop_live_stream()

    log = _log(win)
    assert "Kayitta 1 bosluk, toplam 4 pencere gelmedi." in log
    assert "3..6 arasi 4 pencere gelmedi" in log


def test_several_gaps_are_all_reported(win: MainWindow, tmp_path: Path) -> None:
    source = _WindowSource([0, 1, 5, 6, 20])
    _stream(win, source, tmp_path, expected=5)
    win.stop_recording(ClosureReason.DISCONNECTED)
    win.stop_live_stream()

    log = _log(win)
    # 2..4 (3 pencere) ve 7..19 (13 pencere) = 16
    assert "Kayitta 2 bosluk, toplam 16 pencere gelmedi." in log
    assert "2..4 arasi 3 pencere gelmedi" in log
    assert "7..19 arasi 13 pencere gelmedi" in log


def test_a_run_without_gaps_says_so_explicitly(win: MainWindow, tmp_path: Path) -> None:
    """Sessizlik "boşluk yok" anlamına gelmemeli; açıkça yazılır."""
    source = _WindowSource(list(range(8)))
    _stream(win, source, tmp_path, expected=8)
    win.stop_recording()
    win.stop_live_stream()

    assert "Kayitta bosluk yok: butun pencereler yazildi." in _log(win)


def test_a_gap_across_a_file_rotation_is_still_visible(win: MainWindow, tmp_path: Path) -> None:
    """Dosya değişse bile boşluk kaybolmaz: ölçü mutlak ızgaradır."""
    source = _WindowSource([0, 1, 2, 3, 10, 11])
    win.set_live_source(source)
    win.start_live_stream()
    recorder = win.start_recording(
        tmp_path, policy=RotationPolicy(max_bytes=HEADER_BYTES + 2 * RECORD_BYTES)
    )
    pumped = 0
    for _ in range(3000):
        pumped += win.pump_live_stream(limit=8)
        if pumped >= 6:
            break
        win.thread().msleep(1)
    win.stop_recording(ClosureReason.DISCONNECTED)
    win.stop_live_stream()

    assert len(recorder.paths) > 1  # gercekten dosya degisti
    assert recorder.missing_windows == 6  # 4..9
    assert "4..9 arasi 6 pencere gelmedi" in _log(win)


def test_the_records_around_a_gap_are_all_readable(win: MainWindow, tmp_path: Path) -> None:
    """Boşluk veri kaybettirmez: gelen her pencere dosyada tam olarak durur."""
    source = _WindowSource([0, 1, 2, 7, 8, 9])
    _stream(win, source, tmp_path, expected=6)
    win.stop_recording(ClosureReason.DISCONNECTED)
    win.stop_live_stream()

    written = next(iter(tmp_path.glob("*.bin")))
    assert _records(written) == [0, 1, 2, 7, 8, 9]  # sira zamandan turer
