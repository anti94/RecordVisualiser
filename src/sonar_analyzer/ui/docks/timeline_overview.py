"""Kayıt geneli Timeline özeti — `F3-054`, `F3-055` (plan Bölüm 5.6).

Tüm kayıt aralığını yatay bir şerit olarak gösterir: başlangıç ve bitiş
uçları, üzerinde olay yoğunluğu (zaman kovalarına düşen olay sayısı) bir
mini histogram olarak çizilir.

Konum eşlemesi `x_fraction_for_ns()` ile dışarıya verilir: başlangıç
`0.0`, bitiş `1.0`, aradaki her an oransal yerine düşer — çizim ve
testler aynı eşlemeyi kullanır.

`F3-055`: şerit üzerinde **viewport** dikdörtgeni, grafiklerin o an
gösterdiği zaman dilimini işaretler. Kullanıcı sürükleyince
`viewport_changed(start_ns, end_ns)` yayılır; grafik X aralığı buradan
kaydırılır ve (X-senkronluysa) tüm bağlı grafikler birlikte gider.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
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

    #: `F3-055` viewport sürüklendi — (start_ns, end_ns) mutlak epoch-ns.
    #: `object` (64-bit): C++ 32-bit `int`'e sığmaz.
    viewport_changed = Signal(object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(WIDGET_OBJECT_NAME)
        self.setMinimumHeight(26)
        self._range: TimeRange | None = None
        self._event_times_ns: tuple[int, ...] = ()
        #: Grafiklerin gösterdiği dilim, kayıt aralığına oransal (0..1).
        self._viewport: tuple[float, float] | None = None
        self._dragging = False
        self._drag_grab_fraction = 0.0

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
        self._viewport = None
        self._dragging = False
        self.update()

    # -- viewport (F3-055) -----------------------------------------

    def set_viewport_ns(self, start_ns: int, end_ns: int) -> None:
        """Grafiklerin gösterdiği dilimi işaretler — **yayınlamadan** — `F3-055`.

        Grafik X aralığı değiştiğinde çağrılır; sürükleme sırasında
        (`_dragging`) yok sayılır ki kullanıcının hareketi zıplamasın.
        """
        if self._range is None or self._range.duration_ns <= 0 or self._dragging:
            return
        lo, hi = sorted((start_ns, end_ns))
        self._viewport = (
            self.x_fraction_for_ns(lo),
            self.x_fraction_for_ns(hi),
        )
        self.update()

    def viewport_ns(self) -> tuple[int, int] | None:
        """Viewport'un mutlak epoch-ns `(start, end)` sınırları; yoksa `None`."""
        if self._viewport is None or self._range is None:
            return None
        lo_f, hi_f = self._viewport
        return self._ns_for_fraction(lo_f), self._ns_for_fraction(hi_f)

    def clear_viewport(self) -> None:
        self._viewport = None
        self.update()

    def _ns_for_fraction(self, fraction: float) -> int:
        assert self._range is not None
        return self._range.start_ns + round(fraction * self._range.duration_ns)

    def drag_viewport_to(self, centre_fraction: float) -> None:
        """Sürükleme jestinin programatik karşılığı: viewport'u taşı ve yay — `F3-055`."""
        self._dragging = True
        try:
            self._move_viewport_centre_to(centre_fraction)
        finally:
            self._dragging = False

    def _move_viewport_centre_to(self, centre_fraction: float) -> None:
        """Viewport'u (genişliğini koruyarak) verilen merkeze taşır ve yayar."""
        if self._viewport is None or self._range is None:
            return
        lo_f, hi_f = self._viewport
        half = (hi_f - lo_f) / 2.0
        centre = min(max(half, centre_fraction), 1.0 - half)
        self._viewport = (centre - half, centre + half)
        self.update()
        self.viewport_changed.emit(
            self._ns_for_fraction(centre - half),
            self._ns_for_fraction(centre + half),
        )

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

    # -- fare (F3-055 sürükle) ------------------------------------

    def _pixel_to_fraction(self, x_pixel: float) -> float:
        width = max(1, self.width() - 2 * _TRACK_MARGIN)
        return min(max((x_pixel - _TRACK_MARGIN) / width, 0.0), 1.0)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # Qt override
        if event.button() != Qt.MouseButton.LeftButton or self._viewport is None:
            super().mousePressEvent(event)
            return
        self._dragging = True
        self._move_viewport_centre_to(self._pixel_to_fraction(event.position().x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # Qt override
        if self._dragging:
            self._move_viewport_centre_to(self._pixel_to_fraction(event.position().x()))
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # Qt override
        self._dragging = False
        super().mouseReleaseEvent(event)

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

        if self._viewport is not None:
            lo_f, hi_f = self._viewport
            vx = _TRACK_MARGIN + lo_f * width
            vw = max(2.0, (hi_f - lo_f) * width)
            colour = QColor(DARK.accent)
            colour.setAlpha(60)
            painter.setBrush(colour)
            painter.drawRect(QRectF(vx, _TRACK_MARGIN, vw, self.height() - 2 * _TRACK_MARGIN))
        painter.end()
