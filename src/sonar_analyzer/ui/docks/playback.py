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
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.application.event_navigation import (
    clamp_time_ns,
    next_event,
    previous_event,
)
from sonar_analyzer.application.playback_state import PlaybackMachine
from sonar_analyzer.domain.event import Event
from sonar_analyzer.domain.time_range import NS_PER_SECOND, RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.ui.docks.playback_clock import PlaybackClock
from sonar_analyzer.ui.docks.timeline_overview import TimelineOverview

#: Kayıt periyodu saniye cinsinden (125 ms ızgara).
RECORD_PERIOD_S = RECORD_PERIOD_NS / NS_PER_SECOND

#: `F3-058` oynatma hızı çarpanları (0.25x–10x).
PLAYBACK_SPEEDS: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
DEFAULT_PLAYBACK_SPEED = 1.0


def _speed_label(multiplier: float) -> str:
    return f"{multiplier:g}x"


DOCK_OBJECT_NAME = "dock_playback"
DOCK_TITLE = "Playback / Time Control"

#: Kaydiriciyi tamsayi tutmak icin kullanilan cozunurluk (1 adim = 1 ms).
SLIDER_STEPS_PER_SECOND = 1000

#: (nesne adi, etiket, ipucu) — mockup sirasiyla; sondaki iki dugme
#: `F3-059` ile eklendi (komsu olaya atla).
TRANSPORT_BUTTONS: tuple[tuple[str, str, str], ...] = (
    ("button_skip_start", "|<", "Basa sar"),
    ("button_play", ">", "Oynat / duraklat"),
    ("button_loop", "O", "Secili araligi dongude oynat"),
    ("button_forward", ">>", "Ileri sar"),
    ("button_skip_end", ">|", "Sona git"),
    ("button_prev_event", "‹E", "Onceki olaya git"),
    ("button_next_event", "E›", "Sonraki olaya git"),
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
    #: `F3-058` oynatma hızı çarpanı değişti.
    speed_changed = Signal(float)
    #: `F3-059` komşu olaya atlandı; yük = hedef `Event`.
    event_navigated = Signal(object)

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
        #: F3-059: kayıt başlangıcının kanonik ns'si (olay zamanları mutlaktır).
        self._recording_start_ns = 0
        #: F3-059: komşu olaya atlamada kullanılan olaylar (zaman sırasız olabilir).
        self._events: list[Event] = []
        #: F3-056: saf oynatma durum makinesi (play/pause/stop).
        self.machine = PlaybackMachine(0.0)
        #: F3-057: PLAYING iken makineyi kayıt zamanına göre ilerleten saat.
        self.clock = PlaybackClock(self.machine, parent=self)
        self.machine.add_listener(self._on_machine_changed)
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
        # F3-059: komşu olaya atla.
        self.buttons["button_prev_event"].clicked.connect(lambda: self.goto_previous_event())
        self.buttons["button_next_event"].clicked.connect(lambda: self.goto_next_event())

        # F3-058: oynatma hızı seçici (0.25x–10x).
        self.speed_selector = QComboBox(body)
        self.speed_selector.setObjectName("combo_playback_speed")
        for multiplier in PLAYBACK_SPEEDS:
            self.speed_selector.addItem(_speed_label(multiplier), multiplier)
        self.speed_selector.setCurrentIndex(PLAYBACK_SPEEDS.index(DEFAULT_PLAYBACK_SPEED))
        self.speed_selector.currentIndexChanged.connect(self._on_speed_changed)
        layout.addWidget(self.speed_selector)

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
        # F3-057: 125 ms kayıt ızgarasının sınır zamanları.
        boundary_count = int(self._duration_s / RECORD_PERIOD_S + 1e-9) + 1
        self.machine.set_record_boundaries(
            tuple(i * RECORD_PERIOD_S for i in range(boundary_count))
        )

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
        self._recording_start_ns = time_range.start_ns
        self.set_duration(time_range.duration_ns / NS_PER_SECOND)
        self.timeline.set_recording(time_range)

    def set_events(self, events: Sequence[Event]) -> None:
        """Overview timeline'ın olay yoğunluğunu ve komşu-olay atlamasını besler.

        `F3-054` yoğunluk şeridi + `F3-059` önceki/sonraki olay.
        """
        self._events = list(events)
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
        # Kaydırıcı önce güncellenir ki `position_changed` bir kez yayılsın;
        # ardından makine aynı konuma aranır (F3-057 sınır indeksi için).
        self.slider.setValue(round(clamped * SLIDER_STEPS_PER_SECOND))
        self.machine.seek(clamped)

    # -- gezinme (F3-059) ----------------------------------------------

    def _current_abs_ns(self) -> int:
        """İmlecin kanonik (mutlak) ns konumu."""
        return self._recording_start_ns + round(self.position_s * NS_PER_SECOND)

    def _abs_to_position_s(self, abs_ns: int) -> float:
        return (abs_ns - self._recording_start_ns) / NS_PER_SECOND

    def goto_time_ns(self, abs_ns: int) -> None:
        """İmleci kanonik bir zamana taşır; sınır dışı zaman **güvenle** kenetlenir.

        `F3-059` — kabul: sınır dışı zaman güvenli sınırlanır.
        """
        end_ns = self._recording_start_ns + round(self._duration_s * NS_PER_SECOND)
        safe_ns = clamp_time_ns(abs_ns, self._recording_start_ns, end_ns)
        self.set_position(self._abs_to_position_s(safe_ns))

    def goto_previous_event(self) -> bool:
        """İmleçten **kesin olarak önceki** olaya atlar; yoksa `False` — `F3-059`."""
        target = previous_event(self._events, self._current_abs_ns())
        if target is None:
            return False
        self.set_position(self._abs_to_position_s(target.timestamp_ns))
        self.event_navigated.emit(target)
        return True

    def goto_next_event(self) -> bool:
        """İmleçten **kesin olarak sonraki** olaya atlar; yoksa `False` — `F3-059`."""
        target = next_event(self._events, self._current_abs_ns())
        if target is None:
            return False
        self.set_position(self._abs_to_position_s(target.timestamp_ns))
        self.event_navigated.emit(target)
        return True

    @property
    def is_playing(self) -> bool:
        return self.machine.is_playing

    @property
    def playback_speed(self) -> float:
        """Seçili oynatma hızı çarpanı — `F3-058`."""
        return self.clock.speed

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

    def _on_machine_changed(self) -> None:
        """`F3-057` — saat makineyi ilerletince kaydırıcı/etiket onu izler."""
        target = round(self.machine.position_s * SLIDER_STEPS_PER_SECOND)
        if self.slider.value() != target:
            self._updating = True
            self.slider.setValue(target)
            self._updating = False
        self.buttons["button_play"].setText("||" if self.machine.is_playing else ">")
        if not self.machine.is_playing and self.buttons["button_play"].isChecked():
            self.buttons["button_play"].setChecked(False)
        self._refresh_label()

    def _on_speed_changed(self, index: int) -> None:
        """Hız seçicisi değişince saati ölçekler ve sinyal yayar — `F3-058`."""
        if index < 0 or index >= len(PLAYBACK_SPEEDS):
            return
        multiplier = PLAYBACK_SPEEDS[index]
        self.clock.set_speed(multiplier)
        self.speed_changed.emit(multiplier)

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
