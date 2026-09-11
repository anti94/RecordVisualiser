"""Record/Stop durumunun ana ekrana bağlanması — `F5-032`.

Kabul: **aktif dosya, geçen süre ve kayıt durumu görünür.**

Üçü de gerçek bir kayıttan doğrulanır: canlı kaynak takılır, `Record`
başlatılır, paketler `pump_live_stream()` ile akıtılır ve ekranda görünen
dosya adı, süre ve durumun **diskteki gerçekle** aynı olduğu gösterilir.
Ekrandaki değerleri yazıcıya sormadan üretmek, arayüzün diskten
ayrışabilmesi demek olurdu; bu yüzden dosya adı `tmp_path` içinde gerçekten
aranır ve süre paket sayısından elle hesaplanır.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.session import RecordingState
from sonar_analyzer.ui.cards.recording_status import (
    EMPTY_VALUE,
    RecordingStatus,
    RecordingStatusCard,
    format_elapsed,
)
from sonar_analyzer.ui.main_window import MainWindow

START_NS = 1_788_901_200_000_000_000
CHANNELS = tuple(
    ChannelMetadata(id=f"ch{index}", path=f"/ch{index}", name=f"Kanal {index}", dtype="float32")
    for index in range(8)
)


class _ScriptedSource:
    """Verilen sayıda 125 ms penceresi üreten canlı kaynak."""

    def __init__(self, window_count: int) -> None:
        self._window_count = window_count
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

    def packets(self):
        for window in range(self._window_count):
            yield _packet(window)


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


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def _run_recording(win: MainWindow, tmp_path: Path, windows: int) -> None:
    """Kaynağı takar, kaydı başlatır ve bütün paketleri akıtır."""
    win.set_live_source(_ScriptedSource(windows))
    win.start_live_stream()
    win.start_recording(tmp_path)
    qtbot_wait_for_packets(win, windows)


def qtbot_wait_for_packets(win: MainWindow, expected: int) -> None:
    """Worker bütün paketleri kuyruğa koyana kadar pompalar."""
    pumped = 0
    for _ in range(2000):
        pumped += win.pump_live_stream(limit=8)
        if pumped >= expected:
            return
        win.thread().msleep(1)
    raise AssertionError(f"yalniz {pumped}/{expected} paket pompalandi")


# --------------------------------------------------------------------------- #
# kart: bicimlendirme, hicbir sey turetmez
# --------------------------------------------------------------------------- #


def test_an_untouched_card_shows_no_values(qtbot: QtBot) -> None:
    card = RecordingStatusCard()
    qtbot.addWidget(card)
    for name in card.field_names():
        assert card.field_value(name) == EMPTY_VALUE


def test_the_card_shows_the_state_the_file_and_the_elapsed_time(qtbot: QtBot) -> None:
    card = RecordingStatusCard()
    qtbot.addWidget(card)
    card.update_status(
        RecordingStatus(
            state=RecordingState.RECORDING,
            path=Path("C:/kayitlar/Data_001.bin"),
            elapsed_ns=3_723 * 1_000_000_000,
            record_count=42,
            dropped_records=0,
            file_count=1,
        )
    )

    assert card.field_value("state") == "Kayit suruyor"
    assert card.field_value("file") == "Data_001.bin"
    assert card.field_value("elapsed") == "01:02:03"
    assert card.field_value("records") == "42"
    assert card.field_value("dropped") == "0"
    assert card.field_value("files") == "1"


def test_a_failed_recording_never_looks_like_a_running_one(qtbot: QtBot) -> None:
    """`F5-030`'un kuralı kartta da geçerli: hata "kayıt sürüyor" görünmez."""
    card = RecordingStatusCard()
    qtbot.addWidget(card)
    card.update_status(
        RecordingStatus(
            state=RecordingState.FAILED,
            path=Path("Data_001.bin"),
            record_count=120,
            error="Diskte yer kalmadi",
        )
    )

    assert card.field_value("state") == "HATA: Diskte yer kalmadi"
    assert "suruyor" not in card.field_value("state")


def test_a_missing_counter_shows_a_dash_not_a_zero(qtbot: QtBot) -> None:
    """ "Kayıt yok" ile "sıfır kayıt" farklıdır."""
    card = RecordingStatusCard()
    qtbot.addWidget(card)
    card.update_status(RecordingStatus())

    assert card.field_value("records") == EMPTY_VALUE
    assert card.field_value("elapsed") == EMPTY_VALUE
    assert card.field_value("state") == "Kayit yok"


@pytest.mark.parametrize(
    ("elapsed_ns", "expected"),
    [
        (0, "00:00:00"),
        (999_999_999, "00:00:00"),  # 1 saniyeden kisa
        (1_000_000_000, "00:00:01"),
        (59 * 1_000_000_000, "00:00:59"),
        (60 * 1_000_000_000, "00:01:00"),
        (3600 * 1_000_000_000, "01:00:00"),
        (36_000 * 1_000_000_000, "10:00:00"),
    ],
)
def test_the_elapsed_format_is_hours_minutes_seconds(elapsed_ns: int, expected: str) -> None:
    assert format_elapsed(elapsed_ns) == expected


def test_a_negative_elapsed_is_refused() -> None:
    with pytest.raises(ValueError, match="elapsed_ns negatif olamaz"):
        format_elapsed(-1)


# --------------------------------------------------------------------------- #
# eylemler: Record ve Stop
# --------------------------------------------------------------------------- #


def test_record_is_disabled_until_a_live_source_is_attached(win: MainWindow) -> None:
    assert win.action("action_record").isEnabled() is False
    assert win.action("action_stop_recording").isEnabled() is False


def test_attaching_a_source_enables_record_only(win: MainWindow) -> None:
    win.set_live_source(_ScriptedSource(0))
    assert win.action("action_record").isEnabled() is True
    assert win.action("action_stop_recording").isEnabled() is False


def test_starting_a_recording_swaps_which_action_is_enabled(
    win: MainWindow, tmp_path: Path
) -> None:
    win.set_live_source(_ScriptedSource(0))
    win.start_recording(tmp_path)
    try:
        assert win.action("action_record").isEnabled() is False
        assert win.action("action_stop_recording").isEnabled() is True
    finally:
        win.stop_recording()

    assert win.action("action_record").isEnabled() is True
    assert win.action("action_stop_recording").isEnabled() is False


def test_recording_without_a_source_is_refused(win: MainWindow, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="canli kaynak takilmali"):
        win.start_recording(tmp_path)


def test_starting_twice_is_refused(win: MainWindow, tmp_path: Path) -> None:
    win.set_live_source(_ScriptedSource(0))
    win.start_recording(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="Kayit zaten suruyor"):
            win.start_recording(tmp_path)
    finally:
        win.stop_recording()


def test_a_cancelled_directory_dialog_starts_nothing(win: MainWindow) -> None:
    win.set_live_source(_ScriptedSource(0))
    win.recording_directory_dialog = lambda: ""

    assert win.prompt_start_recording() is None
    assert win.recording_active is False


def test_the_dialog_choice_is_where_the_recording_lands(win: MainWindow, tmp_path: Path) -> None:
    win.set_live_source(_ScriptedSource(0))
    target = tmp_path / "secilen"
    target.mkdir()
    win.recording_directory_dialog = lambda: str(target)

    recorder = win.prompt_start_recording()
    try:
        assert recorder is not None
        assert win.recording_active is True
    finally:
        win.stop_recording()


# --------------------------------------------------------------------------- #
# AKTIF DOSYA, GECEN SURE VE KAYIT DURUMU GORUNUR
# --------------------------------------------------------------------------- #


def test_the_active_file_shown_is_the_file_on_disk(win: MainWindow, tmp_path: Path) -> None:
    _run_recording(win, tmp_path, windows=8)
    shown = win.right_dock.recording_status.field_value("file")
    win.stop_recording()
    win.stop_live_stream()

    written = sorted(path.name for path in tmp_path.glob("*.bin"))
    assert written == [shown]  # ekrandaki ad diskteki dosyanin adi
    assert shown == "Data_001.bin"


def test_the_elapsed_time_matches_the_recorded_span(win: MainWindow, tmp_path: Path) -> None:
    """8 pencere = 7 × 125 ms aralık; ekrandaki süre bunu gösterir."""
    _run_recording(win, tmp_path, windows=8)
    card = win.right_dock.recording_status
    shown = card.field_value("elapsed")
    win.stop_recording()
    win.stop_live_stream()

    # Elle hesap: ilk pencereden sonuncuya 7 × 125 ms = 875 ms -> 00:00:00
    assert shown == format_elapsed(7 * RECORD_PERIOD_NS)
    assert shown == "00:00:00"


def test_a_longer_run_shows_a_growing_elapsed_time(win: MainWindow, tmp_path: Path) -> None:
    """Süre veriden türetilir: 25 pencere = 3 s aralık."""
    _run_recording(win, tmp_path, windows=25)
    shown = win.right_dock.recording_status.field_value("elapsed")
    win.stop_recording()
    win.stop_live_stream()

    assert shown == "00:00:03"  # 24 x 125 ms = 3.000 s


def test_the_state_says_recording_while_it_records(win: MainWindow, tmp_path: Path) -> None:
    _run_recording(win, tmp_path, windows=4)
    try:
        assert win.right_dock.recording_status.field_value("state") == "Kayit suruyor"
        assert win.recording_active is True
    finally:
        win.stop_recording()
        win.stop_live_stream()


def test_the_state_says_stopped_after_stop(win: MainWindow, tmp_path: Path) -> None:
    _run_recording(win, tmp_path, windows=4)
    win.stop_recording()
    win.stop_live_stream()

    assert win.right_dock.recording_status.field_value("state") == "Durduruldu"
    assert win.recording_active is False


def test_the_record_count_on_screen_matches_the_file(win: MainWindow, tmp_path: Path) -> None:
    """Ekrandaki sayı ile dosyadaki kayıt sayısı ayrışamaz."""
    _run_recording(win, tmp_path, windows=12)
    shown = win.right_dock.recording_status.field_value("records")
    outcomes = win.stop_recording()
    win.stop_live_stream()

    written = next(iter(tmp_path.glob("*.bin")))
    raw = written.read_bytes()
    read_validated_header(raw)
    on_disk = (len(raw) - 36) // 68
    assert int(shown) == on_disk == 12
    assert sum(outcome.record_count for outcome in outcomes) == 12


def test_the_status_bar_and_the_card_agree(win: MainWindow, tmp_path: Path) -> None:
    """İki yüzey de tek bir `RecordingStatus`'tan türer — `F5-019` ile aynı ilke."""
    _run_recording(win, tmp_path, windows=6)
    try:
        bar_text = win.status.field_value("recording")
        card = win.right_dock.recording_status
        assert bar_text.startswith("REC ")
        assert card.field_value("file") in bar_text
        assert card.field_value("records") in bar_text
    finally:
        win.stop_recording()
        win.stop_live_stream()


def test_the_status_bar_shows_no_value_when_nothing_was_recorded(win: MainWindow) -> None:
    """Değeri olmayan alan gizlenmez, `—` gösterir (durum çubuğunun kuralı)."""
    assert win.status.field_value("recording") == EMPTY_VALUE


def test_stopping_reports_the_outcome_in_the_log(win: MainWindow, tmp_path: Path) -> None:
    _run_recording(win, tmp_path, windows=5)
    outcomes = win.stop_recording()
    win.stop_live_stream()

    log = "\n".join(win.bottom_dock.log_lines())
    assert outcomes and outcomes[0].succeeded is True
    assert "Kayit tamamlandi" in log


def test_the_recording_card_lives_in_the_live_tab(win: MainWindow) -> None:
    """Varsayılan düzen değişmez; kart canlı kaynak takılınca görünür."""
    assert win.right_dock.live_tab_is_open is False
    win.set_live_source(_ScriptedSource(0))
    assert win.right_dock.live_tab_is_open is True
    assert win.right_dock.card_titles() == [
        "BIT / System Status",
        "Analysis Tools",
        "Data Export",
    ]


def test_detaching_the_source_clears_the_recording_card(win: MainWindow) -> None:
    win.set_live_source(_ScriptedSource(0))
    win.right_dock.recording_status.update_status(
        RecordingStatus(state=RecordingState.RECORDING, record_count=3)
    )
    win.set_live_source(None)

    assert win.right_dock.recording_status.field_value("records") == EMPTY_VALUE
