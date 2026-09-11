"""Canlı modda mockup pano davranışı — `F5-040`.

Kabul: **Ana yerleşim korunur; bağlantı ve kayıt durumu açıkça görünür.**

Faz 5 boyunca panoya üç yeni yüzey eklendi (canlı sekmesi, kayıt kartı,
durum çubuğu alanı) ve toolbar'a iki eylem. Bu dosya, hepsinin
*eklendikten sonra* mockup yerleşimini bozmadığını gösterir: canlı akış
sürerken ve kayıt alınırken `docs/ui/layout-map.md` §2'nin dokuz bölgesi
hâlâ yerinde ve görünürdür.

Ölçüt `F3-079`'un testiyle **aynı** bölge tablosu ve aynı alan
hesabıdır; farklı bir ölçüt kullanmak, yerleşimin bozulmadığını değil
yalnız yeni ölçütün sağlandığını gösterirdi.

"Açıkça görünür" de ölçülür: durum çubuğu ile araç çubuğu aynı bağlantı
durumunu söyler, kayıt sürerken durum çubuğunda ve kartta aynı dosya ve
aynı kayıt sayısı yazar.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.ui.main_window import DEFAULT_WINDOW_SIZE, MainWindow

pytestmark = pytest.mark.gui

#: `docs/ui/layout-map.md` §2 — `F3-079`'un testiyle AYNI tablo.
NINE_REGIONS: tuple[tuple[int, str, str], ...] = (
    (1, "Dosya ve Veri Yönetimi", "left"),
    (2, "Hızlı Araçlar", "center"),
    (3, "Görselleştirme Alanı", "center"),
    (4, "Donanım/BIT Durumu", "right"),
    (5, "Hesaplamalar ve Analiz", "right"),
    (6, "Çoklu Görünüm", "center"),
    (7, "Zaman Kontrolü", "bottom"),
    (8, "Log / Mesajlar", "bottom"),
    (9, "Ayarlar ve Dışa Aktarma", "right"),
)

START_NS = 1_788_901_200_000_000_000
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


class _ScriptedSource:
    def __init__(self, count: int) -> None:
        self._count = count
        self.state = ConnectionState.CONNECTED
        self._stats = LiveStats()

    def channels(self) -> Sequence[ChannelMetadata]:
        return CHANNELS

    def stats(self) -> LiveStats:
        return self._stats

    def connect(self) -> None:
        self.state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self.state = ConnectionState.DISCONNECTED

    def packets(self) -> Iterator[LivePacket]:
        for window in range(self._count):
            yield _packet(window)


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    """`F3-079` ile aynı kurulum — karşılaştırma anlamlı olsun diye."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(*DEFAULT_WINDOW_SIZE)
    window.show()
    qtbot.waitExposed(window)
    window.apply_default_layout()
    return window


def _region_widget(win: MainWindow, number: int) -> QWidget:
    return {
        1: win.left_dock,
        2: win.plot_tool_bar,
        3: win.dashboard,
        4: win.right_dock.bit_status,
        5: win.right_dock.cards["card_analysis_tools"],
        6: win.view_tabs,
        7: win.playback_dock,
        8: win.bottom_dock.log,
        9: win.right_dock.data_export,
    }[number]


def _area_of(win: MainWindow, widget: QWidget) -> str:
    centre: QPoint = widget.mapTo(win, widget.rect().center())
    mid_x, mid_y = win.width() / 2, win.height() / 2
    if centre.x() < mid_x * 0.55:
        return "left"
    if centre.x() > mid_x * 1.45:
        return "right"
    return "bottom" if centre.y() > mid_y * 1.25 else "center"


def _go_live(win: MainWindow, *, windows: int = 12) -> None:
    """Kaynağı takar, akışı başlatır ve paketleri pompalar."""
    win.set_live_source(_ScriptedSource(windows))
    win.connect_live_source()
    win.set_live_plot_channel("ch0")
    win.start_live_stream()
    pumped = 0
    for _ in range(3000):
        pumped += win.pump_live_stream(limit=8)
        if pumped >= windows:
            return
        win.thread().msleep(1)
    raise AssertionError(f"yalniz {pumped}/{windows} paket pompalandi")


# --------------------------------------------------------------------------- #
# ANA YERLESIM KORUNUR
# --------------------------------------------------------------------------- #


def test_all_nine_regions_survive_live_mode(win: MainWindow) -> None:
    """Canlı akış sürerken dokuz bölge hâlâ görünür."""
    _go_live(win)
    try:
        for number, label, _area in NINE_REGIONS:
            widget = _region_widget(win, number)
            assert widget.isVisibleTo(win), f"canli modda bolge {number} ({label}) gorunmuyor"
    finally:
        win.stop_live_stream()


@pytest.mark.parametrize(("number", "label", "expected_area"), NINE_REGIONS)
def test_each_region_stays_in_its_mockup_area_during_live(
    win: MainWindow, number: int, label: str, expected_area: str
) -> None:
    _go_live(win)
    try:
        widget = _region_widget(win, number)
        assert _area_of(win, widget) == expected_area, f"bolge {number} ({label}) kaydi"
    finally:
        win.stop_live_stream()


def test_the_three_column_layout_survives_live_mode(win: MainWindow) -> None:
    _go_live(win)
    try:
        left, center, right = win.column_widths()
        assert left < center and right < center  # merkez hala en genis
        assert win.playback_dock.y() < win.bottom_dock.y()
    finally:
        win.stop_live_stream()


def test_the_overview_cards_keep_their_order_in_live_mode(win: MainWindow) -> None:
    """Canlı sekmesi eklendi ama Overview kart sırası değişmedi."""
    _go_live(win)
    try:
        assert win.right_dock.card_titles() == [
            "BIT / System Status",
            "Analysis Tools",
            "Data Export",
        ]
    finally:
        win.stop_live_stream()


def test_recording_does_not_disturb_the_layout(win: MainWindow, tmp_path: Path) -> None:
    """Kayıt da başlasa yerleşim aynı kalır."""
    _go_live(win)
    win.start_recording(tmp_path)
    try:
        for number, label, expected_area in NINE_REGIONS:
            widget = _region_widget(win, number)
            assert widget.isVisibleTo(win), f"kayit sirasinda bolge {number} ({label}) kayboldu"
            assert _area_of(win, widget) == expected_area
    finally:
        win.stop_recording()
        win.stop_live_stream()


def test_the_live_tab_is_extra_not_a_replacement(win: MainWindow) -> None:
    """Canlı sekmesi Overview'in yerini almaz, yanına eklenir."""
    before = win.right_dock.tab_titles()
    _go_live(win)
    try:
        after = win.right_dock.tab_titles()
        assert before[0] == after[0]  # Overview hala ilk sekme
        assert "Live" in after
        assert len(after) == len(before) + 1
    finally:
        win.stop_live_stream()


# --------------------------------------------------------------------------- #
# BAGLANTI VE KAYIT DURUMU ACIKCA GORUNUR
# --------------------------------------------------------------------------- #


def test_the_connection_state_is_visible_in_the_status_bar(win: MainWindow) -> None:
    _go_live(win)
    try:
        assert win.status.field_value("connection").strip() != ""
        assert win.connection_state() is ConnectionState.CONNECTED
    finally:
        win.stop_live_stream()


def test_the_toolbar_and_the_status_bar_agree_about_the_connection(win: MainWindow) -> None:
    """İki yüzey tek kaynaktan türer (`F5-019`); ayrışamazlar."""
    _go_live(win)
    try:
        assert win.action("action_connect").isEnabled() is False  # zaten bagli
        assert win.action("action_disconnect").isEnabled() is True
    finally:
        win.stop_live_stream()
    win.disconnect_live_source()

    assert win.action("action_connect").isEnabled() is True
    assert win.action("action_disconnect").isEnabled() is False


def test_the_recording_state_is_visible_while_recording(win: MainWindow, tmp_path: Path) -> None:
    _go_live(win)
    win.start_recording(tmp_path)
    try:
        assert win.status.field_value("recording").startswith("REC")
        assert win.right_dock.recording_status.field_value("state") == "Kayit suruyor"
    finally:
        win.stop_recording()
        win.stop_live_stream()


def test_the_status_bar_and_the_card_show_the_same_recording(
    win: MainWindow, tmp_path: Path
) -> None:
    """Aynı dosya ve aynı sayı; iki yüzey tek `RecordingStatus`'tan gelir."""
    # Kayit AKIS BASLAMADAN once acilir; yoksa paketler kayda hic ugramaz
    # ve dosya olusmaz (dosya ilk kayitla birlikte acilir, `F5-031`).
    win.set_live_source(_ScriptedSource(12))
    win.connect_live_source()
    win.set_live_plot_channel("ch0")
    win.start_live_stream()
    win.start_recording(tmp_path)
    try:
        pumped = 0
        for _ in range(3000):
            pumped += win.pump_live_stream(limit=8)
            if pumped >= 12:
                break
            win.thread().msleep(1)

        bar = win.status.field_value("recording")
        card = win.right_dock.recording_status
        assert card.field_value("file") != "—", "kayit dosyasi olusmadi"
        assert card.field_value("file") in bar
        assert card.field_value("records") in bar
    finally:
        win.stop_recording()
        win.stop_live_stream()


def test_stopping_the_recording_is_visible_too(win: MainWindow, tmp_path: Path) -> None:
    """Durdurma sessiz olmaz; durum "Durduruldu"ya döner."""
    _go_live(win)
    win.start_recording(tmp_path)
    win.stop_recording()
    win.stop_live_stream()

    assert win.right_dock.recording_status.field_value("state") == "Durduruldu"
    assert win.recording_active is False


def test_without_a_live_source_neither_surface_claims_anything(win: MainWindow) -> None:
    """Kaynak yokken bağlantı ve kayıt alanları boş durur — yanlış güven vermez."""
    assert win.right_dock.live_tab_is_open is False
    assert win.status.field_value("connection") in ("", "—")
    assert win.status.field_value("recording") in ("", "—")
    assert win.action("action_record").isEnabled() is False
