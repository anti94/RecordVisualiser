"""Oynatma ilerleme saati — `F3-057`.

`PlaybackMachine` durumu PLAYING iken bir `QTimer` düzenli aralıklarla
tetiklenir ve makinenin konumunu **geçen gerçek süre × hız** kadar
ilerletir. İlerleme sırasında aşılan 125 ms kayıt sınırları makine
tarafından sırayla bildirilir (bkz. `PlaybackMachine.advance`).

Saat yalnız zamanlayıcıdır: sınır sırası mantığı makinede, `GUI olmadan`
test edilir (`F3-056`/`F3-057`).
"""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QObject, QTimer

from sonar_analyzer.application.playback_state import PlaybackMachine

#: Saat tik aralığı (ms). ~30 fps; kayıt zamanı `advance` ile ilerler.
DEFAULT_TICK_MS = 33


class PlaybackClock(QObject):
    """PLAYING iken `machine`'i gerçek zamana göre ilerleten saat."""

    def __init__(
        self,
        machine: PlaybackMachine,
        *,
        tick_ms: int = DEFAULT_TICK_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._machine = machine
        self._speed = 1.0
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(max(1, tick_ms))
        self._timer.timeout.connect(self._tick)
        machine.add_listener(self._sync_to_state)

    @property
    def speed(self) -> float:
        return self._speed

    def set_speed(self, multiplier: float) -> None:
        """Kayıt zamanı ilerleme hızını ölçekler (`F3-058` bağlar)."""
        self._speed = max(0.0, multiplier)

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    def tick_once(self, elapsed_s: float) -> None:
        """Testler için: bir tiki elle sür (gerçek zamanlayıcı beklemeden)."""
        self._machine.advance(elapsed_s * self._speed)

    # -- ic ------------------------------------------------------

    def _sync_to_state(self) -> None:
        if self._machine.is_playing and not self._timer.isActive():
            self._elapsed.restart()
            self._timer.start()
        elif not self._machine.is_playing and self._timer.isActive():
            self._timer.stop()

    def _tick(self) -> None:
        elapsed_s = self._elapsed.restart() / 1000.0
        self._machine.advance(elapsed_s * self._speed)
