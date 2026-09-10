"""Playback / Time Control şeridi — `F1-027`.

Mockup bölge 7 (`docs/ui/layout-map.md` §5): başa sar, oynat, döngü, ileri sar,
sona git; zaman kaydırıcısı; `geçen / toplam`; `Start` ve `End` alanları, birim
`[s]` ve `Go`.

Şerit **merkez grafiklerin altında, Log'un üstünde** durur.

Bu iş yalnız şeridi yerleştirir ve durumunu tutar; gerçek oynatma zamanlayıcısı
sonraki işlerde eklenecektir. Bu yüzden düğmeler sinyal yayar, kendi başlarına
veri oynatmaz.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.application.playback_state import PlaybackMachine
from sonar_analyzer.domain.event import Event
from sonar_analyzer.domain.time_range import NS_PER_SECOND, TimeRange
from sonar_analyzer.ui.docks.timeline_overview import TimelineOverview

DOCK_OBJECT_NAME = "dock_playback"
DOCK_TITLE = "Playback / Time Control"

#: Kaydiriciyi tamsayi tutmak icin kullanilan cozunurluk (1 adim = 1 ms).
SLIDER_STEPS_PER_SECOND = 1000

#: (nesne adi, etiket, ipucu) — mockup sirasiyla.
TRANSPORT_BUTTONS: tuple[tuple[str, str, str], ...] = (
    ("button_skip_start", "|<", "Basa sar"),
    ("button_play", ">", "Oynat / duraklat"),
    ("button_loop", "O", "Secili araligi dongude oynat"),
    ("button_forward", ">>", "Ileri sar"),
    ("button_skip_end", ">|", "Sona git"),
)


def format_elapsed(seconds: float) -> str:
    """`HH:MM:SS` biçiminde süre."""
    total = max(0, round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class PlaybackDock(QDockWidget):
    """Zaman kontrol şeridi."""

    #: Oynat/duraklat durumu degisti (True = oynatiliyor).
    play_toggled = Signal(bool)
    #: Kullanici imleci tasidi; deger saniye cinsinden.
    position_changed = Signal(float)
    #: `Go` ile bir aralik istendi.
    range_requested = Signal(float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(DOCK_TITLE, parent)
        self.setObjectName(DOCK_OBJECT_NAME)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self.buttons: dict[str, QPushButton] = {}
        self._duration_s = 0.0
        #: F3-056: saf oynatma durum makinesi (play/pause/stop).
        self.machine = PlaybackMachine(0.0)
        self._updating = False

        self.setWidget(self._build_body())
        self.set_duration(0.0)

    # -- kurulum ---------------------------------------------------------

    def _build_body(self) -> QWidget:
        body = QWidget(self)
        outer = QVBoxLayout(body)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)

        # F3-054: kayıt geneli overview timeline (uçlar + olay yoğunluğu).
        self.timeline = TimelineOverview(body)
        outer.addWidget(self.timeline)

        transport = QWidget(body)
        layout = QHBoxLayout(transport)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        outer.addWidget(transport)

        for name, text, tooltip in TRANSPORT_BUTTONS:
            button = QPushButton(text, body)
            button.setObjectName(name)
            button.setToolTip(tooltip)
            button.setFixedWidth(36)
            self.buttons[name] = button
            layout.addWidget(button)

        self.buttons["button_play"].setCheckable(True)
        self.buttons["button_play"].toggled.connect(self._on_play_toggled)
        self.buttons["button_loop"].setCheckable(True)
        self.buttons["button_skip_start"].clicked.connect(self._on_stop)
        self.buttons["button_skip_end"].clicked.connect(lambda: self.set_position(self._duration_s))

        self.slider = QSlider(Qt.Orientation.Horizontal, body)
        self.slider.setObjectName("slider_position")
        self.slider.valueChanged.connect(self._on_slider_moved)
        layout.addWidget(self.slider, 1)

        self.time_label = QLabel("00:00:00 / 00:00:00", body)
        self.time_label.setObjectName("label_playback_time")
        layout.addWidget(self.time_label)

        layout.addWidget(QLabel("Start", body))
        self.start_input = self._build_spin(body, "input_range_start")
        layout.addWidget(self.start_input)

        layout.addWidget(QLabel("End", body))
        self.end_input = self._build_spin(body, "input_range_end")
        layout.addWidget(self.end_input)

        layout.addWidget(QLabel("[s]", body))

        self.go_button = QPushButton("Go", body)
        self.go_button.setObjectName("button_go")
        self.go_button.clicked.connect(self._on_go)
        layout.addWidget(self.go_button)

        return body

    def _build_spin(self, parent: QWidget, name: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(parent)
        spin.setObjectName(name)
        spin.setDecimals(3)
        spin.setMaximum(0.0)
        spin.setFixedWidth(90)
        return spin

    # -- durum -----------------------------------------------------------

    def set_duration(self, duration_s: float) -> None:
        """Kayıt süresini uygular; kaydırıcı ve alan sınırlarını günceller."""
        self._duration_s = max(0.0, duration_s)
        self.machine.stop()
        self.machine.set_duration(self._duration_s)

        self._updating = True
        self.slider.setRange(0, round(self._duration_s * SLIDER_STEPS_PER_SECOND))
        self.slider.setValue(0)
        for spin in (self.start_input, self.end_input):
            spin.setMaximum(self._duration_s)
        self.start_input.setValue(0.0)
        self.end_input.setValue(self._duration_s)
        self._updating = False

        self._refresh_label()

        enabled = self._duration_s > 0
        for button in self.buttons.values():
            button.setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self.go_button.setEnabled(enabled)

    def set_recording_range(self, time_range: TimeRange) -> None:
        """Kayıt aralığından süreyi türetir ve overview timeline'ı besler."""
        self.set_duration(time_range.duration_ns / NS_PER_SECOND)
        self.timeline.set_recording(time_range)

    def set_events(self, events: Sequence[Event]) -> None:
        """Overview timeline'ın olay yoğunluğunu günceller — `F3-054`."""
        self.timeline.set_events(events)

    @property
    def duration_s(self) -> float:
        return self._duration_s

    @property
    def position_s(self) -> float:
        return self.slider.value() / SLIDER_STEPS_PER_SECOND

    def set_position(self, seconds: float) -> None:
        """İmleci taşır; sınırların dışına çıkmaz."""
        clamped = min(max(0.0, seconds), self._duration_s)
        self.machine.seek(clamped)
        self.slider.setValue(round(clamped * SLIDER_STEPS_PER_SECOND))

    @property
    def is_playing(self) -> bool:
        return self.machine.is_playing

    def time_text(self) -> str:
        return self.time_label.text()

    # -- olaylar ---------------------------------------------------------

    def _on_play_toggled(self, checked: bool) -> None:
        if checked:
            self.machine.play()
        else:
            self.machine.pause()
        self.buttons["button_play"].setText("||" if self.machine.is_playing else ">")
        self.play_toggled.emit(self.machine.is_playing)

    def _on_stop(self) -> None:
        """`|<` — durdurur ve imleci başa döndürür — `F3-056`."""
        self.machine.stop()
        play_button = self.buttons["button_play"]
        if play_button.isChecked():
            play_button.setChecked(False)  # _on_play_toggled(False) tetikler
        else:
            play_button.setText(">")
        self.set_position(0.0)

    def _on_slider_moved(self, value: int) -> None:
        self._refresh_label()
        if not self._updating:
            self.position_changed.emit(value / SLIDER_STEPS_PER_SECOND)

    def _on_go(self) -> None:
        start = self.start_input.value()
        end = self.end_input.value()
        if end <= start:
            # Ters veya bos aralik reddedilir; sessizce duzeltilmez.
            self.start_input.setToolTip("Bitis, baslangictan buyuk olmali")
            return
        self.start_input.setToolTip("")
        self.set_position(start)
        self.range_requested.emit(start, end)

    def _refresh_label(self) -> None:
        self.time_label.setText(
            f"{format_elapsed(self.position_s)} / {format_elapsed(self._duration_s)}"
        )
