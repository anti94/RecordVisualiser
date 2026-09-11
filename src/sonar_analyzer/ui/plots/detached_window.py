"""Grafiği ayrı bir pencereye ayırma — `F4-082`.

Kullanıcı zaman serisi grafiğini ana pencereden ayırıp ikinci bir ekrana
taşıyabilir, sonra geri takabilir.

**Ayırma bir kopyalama değildir.** Aynı `PlotPanel` widget'ı yeni pencereye
**yeniden ebeveynlenir**. Bunun iki sonucu vardır ve ikisi de kabul
kriterinin karşılığıdır:

* **Veri korunur** — çizili seriler, stiller, işaretler ve zaman ankoru
  aynı nesnede durur; taşınırken hiçbir şey yeniden yüklenmez.
* **X senkronizasyonu korunur** — `x_range_changed` bağlantıları widget'a
  aittir, ebeveynine değil. Ayrılmış panelde yapılan pan/zoom ana
  penceredeki timeline ve bağlı görünümlere aynı şekilde ulaşır.

Kopyalansaydı ikisi de kendiliğinden bozulurdu: ikinci bir panel ayrı
veri tutar ve ayrı sinyaller yayardı.

Pencere kapatıldığında `closed` yayılır; geri takma sorumluluğu
`MainWindow`'undur — pencere kendi kendine yeniden ebeveynlemez.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

WINDOW_TITLE = "Zaman serisi — ayrık pencere"
OBJECT_NAME = "window_detached_plot"


class DetachedPlotWindow(QWidget):
    """Ayrılmış grafiği barındıran üst düzey pencere."""

    #: Pencere kapatıldı — grafik geri takılmalı.
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        # Ebeveyn verilmez: pencere gerçekten bağımsız olmalı ki başka bir
        # monitöre taşınabilsin.
        super().__init__(None)
        self.setObjectName(OBJECT_NAME)
        self.setWindowTitle(WINDOW_TITLE)
        self._owner = parent

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._panel: QWidget | None = None

    @property
    def panel(self) -> QWidget | None:
        """Barındırılan grafik; boşsa `None`."""
        return self._panel

    def take(self, panel: QWidget) -> None:
        """Grafiği bu pencereye alır (yeniden ebeveynleme)."""
        self._panel = panel
        self._layout.addWidget(panel)
        panel.show()

    def release(self) -> QWidget | None:
        """Grafiği bırakır ve döndürür; pencere boş kalır."""
        panel = self._panel
        if panel is not None:
            self._layout.removeWidget(panel)
            panel.setParent(None)
        self._panel = None
        return panel

    def closeEvent(self, event: QCloseEvent) -> None:
        """Kapatma geri takma isteğidir; grafik yok olmaz."""
        self.closed.emit()
        event.accept()
