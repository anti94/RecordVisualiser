"""Kayıt geneli Timeline özeti — `F3-054` (plan Bölüm 5.6).

Tüm kayıt aralığını yatay bir şerit olarak gösterir: başlangıç ve bitiş
uçları, üzerinde olay yoğunluğu (zaman kovalarına düşen olay sayısı) bir
mini histogram olarak çizilir.

Konum eşlemesi `x_fraction_for_ns()` ile dışarıya verilir: başlangıç
`0.0`, bitiş `1.0`, aradaki her an oransal yerine düşer — çizim ve
testler aynı eşlemeyi kullanır.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from sonar_analyzer.domain.event import Event
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.ui.theme import DARK

WIDGET_OBJECT_NAME = "widget_timeline_overview"

#: Yoğunluk histogramı kova sayısı (çizim için).
DENSITY_BUCKETS = 60
_TRACK_MARGIN = 6
_TRACK_HEIGHT = 6


class TimelineOverview(QWidget):
    """Kayıt aralığını ve olay yoğunluğunu gösteren overview şeridi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(WIDGET_OBJECT_NAME)
        self.setMinimumHeight(26)
        self._range: TimeRange | None = None
        self._event_times_ns: tuple[int, ...] = ()

    # -- veri ------------------------------------------------------------

    def set_recording(self, time_range: TimeRange) -> None:
        """Timeline'ın kapsadığı kayıt aralığını belirler — `F3-054`."""
        self._range = time_range
        self.update()

    def set_events(self, events: Sequence[Event]) -> None:
        """Yoğunluk için olay zamanlarını saklar."""
        self._event_times_ns = tuple(sorted(event.timestamp_ns for event in events))
        self.update()

    def clear(self) -> None:
        self._range = None
        self._event_times_ns = ()
        self.update()

    # -- sorgular ------------------------------------------------------

    @property
    def start_ns(self) -> int | None:
        return None if self._range is None else self._range.start_ns

    @property
    def end_ns(self) -> int | None:
        return None if self._range is None else self._range.end_ns

    def x_fraction_for_ns(self, timestamp_ns: int) -> float:
        """`timestamp_ns`'in timeline üzerindeki oransal konumu (0..1) — `F3-054`.

        Başlangıç `0.0`, bitiş `1.0`. Aralık dışı zamanlar `[0, 1]`'e
        kenetlenir. Kayıt yoksa ya da sıfır süreliyse `RuntimeError`.
        """
        if self._range is None or self._range.duration_ns <= 0:
            raise RuntimeError("Timeline araligi yok ya da sifir sureli.")
        raw = (timestamp_ns - self._range.start_ns) / self._range.duration_ns
        return max(0.0, min(1.0, raw))

    def event_density(self, buckets: int = DENSITY_BUCKETS) -> list[int]:
        """Olayları `buckets` eşit zaman kovasına bölüp sayar — `F3-054`.

        Kova indeksi olayın oransal konumundan gelir; bitişteki olay son
        kovaya sayılır (kova sayısı taşmaz).
        """
        if buckets <= 0:
            raise ValueError("Kova sayisi pozitif olmali")
        counts = [0] * buckets
        if self._range is None or self._range.duration_ns <= 0:
            return counts
        for timestamp_ns in self._event_times_ns:
            index = min(buckets - 1, int(self.x_fraction_for_ns(timestamp_ns) * buckets))
            counts[index] += 1
        return counts

    def event_count(self) -> int:
        return len(self._event_times_ns)

    # -- cizim ------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:  # Qt override
        del event
        if self._range is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width() - 2 * _TRACK_MARGIN
        if width <= 0:
            painter.end()
            return
        mid_y = self.height() / 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(DARK.surface_elevated))
        painter.drawRect(QRectF(_TRACK_MARGIN, mid_y - _TRACK_HEIGHT / 2, width, _TRACK_HEIGHT))

        density = self.event_density()
        peak = max(density) or 1
        bar_w = width / len(density)
        painter.setBrush(QColor(DARK.accent))
        for i, count in enumerate(density):
            if not count:
                continue
            height = (self.height() - 2 * _TRACK_MARGIN) * (count / peak)
            x = _TRACK_MARGIN + i * bar_w
            painter.drawRect(QRectF(x, mid_y - height / 2, max(1.0, bar_w - 1), height))
        painter.end()
