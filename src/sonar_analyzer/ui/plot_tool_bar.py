"""Grafik hızlı araç şeridi — `F1-040`.

Mockup bölge 2 (`docs/ui/layout-map.md` §2, §3): araç düğmeleri (pan, zoom,
cursor, ölçüm, seçim, sığdır), zaman penceresi seçici, kanal seçici ve `Sync`
onay kutusu — tek şeritte. Şerit sekme çubuğunun altında, grafik alanının
üstünde durur.

Etkileşim düğmelerinin (pan/zoom/cursor/ölçüm) gerçek davranışı Faz 3'te
bağlanır (`F3-021`..`F3-029`); burada yalnız yerleşimleri hazırdır ve pasif
gösterilirler. Zaman penceresi ve kanal seçici işlevseldir: kanal seçici
gerçek repository kanallarından beslenir ve seçim yapıldığında sinyal yayar.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QToolButton,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE

TOOL_BAR_HEIGHT = 32

#: (nesne adi, etiket, ipucu) — mockup sirasiyla. Faz 3'e kadar pasif.
TOOL_BUTTONS: tuple[tuple[str, str, str], ...] = (
    ("tool_pan", "Pan", "Surukleyerek gorunumu kaydir"),
    ("tool_zoom_x", "Zoom X", "Yatay yakinlastir"),
    ("tool_zoom_y", "Zoom Y", "Dikey yakinlastir"),
    ("tool_zoom_xy", "Zoom XY", "Iki eksende yakinlastir"),
    ("tool_cursor", "Cursor", "Imlec ile deger oku"),
    ("tool_measure", "Measure", "Iki nokta arasi olcum"),
    ("tool_fit", "Fit", "Gorunur veriye sigdir"),
)

#: Zaman penceresi secenekleri (mockup ontanimlisi "1 s").
TIME_WINDOWS: tuple[str, ...] = ("100 ms", "500 ms", "1 s", "5 s", "10 s", "30 s", "60 s")
DEFAULT_TIME_WINDOW = "1 s"

NO_CHANNEL_TEXT = "(kanal yok)"


class PlotToolBar(QWidget):
    """Sekme çubuğunun altında, grafik alanının üstündeki araç şeridi."""

    #: Zaman penceresi metni degisti.
    time_window_changed = Signal(str)
    #: Kanal secici ile bir kanal secildi.
    channel_selected = Signal(str)
    #: Sync onay kutusu degisti.
    sync_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plot_tool_bar")
        self.setFixedHeight(TOOL_BAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self.tool_buttons: dict[str, QToolButton] = {}
        for name, text, tooltip in TOOL_BUTTONS:
            button = QToolButton(self)
            button.setObjectName(name)
            button.setText(text)
            button.setCheckable(True)
            button.setEnabled(False)
            button.setToolTip(f"{tooltip} — {NOT_YET_AVAILABLE}")
            self.tool_buttons[name] = button
            layout.addWidget(button)

        layout.addStretch(1)

        self.time_window = QComboBox(self)
        self.time_window.setObjectName("combo_time_window")
        self.time_window.addItems(TIME_WINDOWS)
        self.time_window.setCurrentText(DEFAULT_TIME_WINDOW)
        self.time_window.currentTextChanged.connect(self.time_window_changed.emit)
        layout.addWidget(self.time_window)

        self.channel_selector = QComboBox(self)
        self.channel_selector.setObjectName("combo_channel_selector")
        self.channel_selector.addItem(NO_CHANNEL_TEXT)
        self.channel_selector.setEnabled(False)
        self.channel_selector.currentIndexChanged.connect(self._on_channel_index_changed)
        layout.addWidget(self.channel_selector)

        self.sync_checkbox = QCheckBox("Sync", self)
        self.sync_checkbox.setObjectName("check_sync")
        self.sync_checkbox.setChecked(True)
        self.sync_checkbox.toggled.connect(self.sync_toggled.emit)
        layout.addWidget(self.sync_checkbox)

        self._channel_ids: list[str] = []

    # -- kanal secici --------------------------------------------------------

    def set_channels(self, channels: list[ChannelMetadata]) -> None:
        """Kanal seçiciyi gerçek kayıttaki kanallarla doldurur."""
        self._channel_ids = [c.id for c in channels]
        self.channel_selector.blockSignals(True)
        self.channel_selector.clear()
        if channels:
            self.channel_selector.addItems([c.display_label for c in channels])
            self.channel_selector.setEnabled(True)
        else:
            self.channel_selector.addItem(NO_CHANNEL_TEXT)
            self.channel_selector.setEnabled(False)
        self.channel_selector.blockSignals(False)

    def set_current_channel(self, channel_id: str) -> None:
        """Görüntülenen kanalı seçiciye yansıtır (sinyal yaymadan)."""
        try:
            index = self._channel_ids.index(channel_id)
        except ValueError:
            return
        self.channel_selector.blockSignals(True)
        self.channel_selector.setCurrentIndex(index)
        self.channel_selector.blockSignals(False)

    def clear_channels(self) -> None:
        self._channel_ids = []
        self.channel_selector.blockSignals(True)
        self.channel_selector.clear()
        self.channel_selector.addItem(NO_CHANNEL_TEXT)
        self.channel_selector.setEnabled(False)
        self.channel_selector.blockSignals(False)

    def _on_channel_index_changed(self, index: int) -> None:
        if 0 <= index < len(self._channel_ids):
            self.channel_selected.emit(self._channel_ids[index])
