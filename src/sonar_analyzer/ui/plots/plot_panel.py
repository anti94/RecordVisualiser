"""Tek kanallı grafik paneli — `F1-031`.

Mockup bölge 3'ün en küçük hâli: bir kanalın zaman serisi, eksen etiketleri ve
birimiyle. PyQtGraph doğrudan kullanılmaz; bu sınıf **soyutlama sınırıdır**
(ADR-002): dışarısı yalnız `DataChunk` ve `ChannelMetadata` görür, PyQtGraph
nesneleri sızmaz.

Zaman ekseni kayıt başlangıcına göre **saniye** cinsindendir. Kanonik `int64`
nanosaniye çizim için doğrudan kullanılamaz: `float32`/`float64`'e çevrildiğinde
mutlak epoch değeri çözünürlüğü yiyor. Bu yüzden panel bir `t0` ankoru tutar ve
görece saniyeye çevirir.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtWidgets import QVBoxLayout, QWidget

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import NS_PER_SECOND
from sonar_analyzer.ui.status_icons import channel_color
from sonar_analyzer.ui.theme import DARK

TIME_AXIS_LABEL = "Time"
TIME_AXIS_UNIT = "s"
EMPTY_TITLE = "Kanal secilmedi"

#: Grid'in gorunurlugu: veri cizgisinden belirgin sekilde daha soluk (plan 6.3).
GRID_ALPHA = 0.15


def to_seconds(timestamps_ns: NDArray[np.int64], t0_ns: int) -> NDArray[np.float64]:
    """Nanosaniye damgalarını `t0`'a göre saniyeye çevirir."""
    return (timestamps_ns - t0_ns).astype(np.float64) / NS_PER_SECOND


class PlotPanel(QWidget):
    """Tek bir kanalı çizen panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plot_panel")

        self._channel: ChannelMetadata | None = None
        self._t0_ns = 0
        self._sample_count = 0

        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget(parent=self)
        self.plot.setObjectName("plot_widget")
        self.plot.setBackground(DARK.surface)
        self.plot.showGrid(x=True, y=True, alpha=GRID_ALPHA)
        self.plot.setLabel("bottom", TIME_AXIS_LABEL, units=TIME_AXIS_UNIT)
        self.plot.setTitle(EMPTY_TITLE, color=DARK.text_secondary)

        self.curve = self.plot.plot([], [], pen=pg.mkPen(DARK.accent, width=1))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)

    # -- veri ------------------------------------------------------------

    def set_channel(self, channel: ChannelMetadata, chunk: DataChunk) -> None:
        """Kanalı ve verisini çizer; başlık ve eksen birimlerini günceller."""
        if chunk.channel_id != channel.id:
            raise ValueError(
                f"Veri baska kanala ait: parca {chunk.channel_id!r}, kanal {channel.id!r}"
            )

        self._channel = channel
        self._sample_count = len(chunk)
        self._t0_ns = chunk.start_ns or 0

        seconds = to_seconds(chunk.timestamps_ns, self._t0_ns)
        values = np.asarray(chunk.values, dtype=np.float64)

        color = channel_color(channel.id)
        self.curve.setPen(pg.mkPen(color, width=1))
        self.curve.setData(seconds, values)

        self.plot.setTitle(channel.display_label, color=DARK.text_primary)
        self.plot.setLabel("left", channel.name, units=channel.unit or "")
        self.plot.setLabel("bottom", TIME_AXIS_LABEL, units=TIME_AXIS_UNIT)
        self.plot.enableAutoRange()

    def clear(self) -> None:
        """Paneli boş duruma döndürür."""
        self._channel = None
        self._sample_count = 0
        self.curve.setData([], [])
        self.plot.setTitle(EMPTY_TITLE, color=DARK.text_secondary)
        self.plot.setLabel("left", "")

    # -- sorgular --------------------------------------------------------

    @property
    def channel(self) -> ChannelMetadata | None:
        return self._channel

    @property
    def sample_count(self) -> int:
        return self._sample_count

    def title_text(self) -> str:
        item = self.plot.getPlotItem().titleLabel
        return str(item.text)

    def axis_label(self, axis: str) -> str:
        """Eksenin etiket metni (birim dahil) — testler ve kabul için."""
        if axis not in ("left", "bottom"):
            raise KeyError(f"Tanimsiz eksen: {axis}")
        return str(self.plot.getPlotItem().getAxis(axis).labelString())

    def curve_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Çizilen (zaman, değer) dizileri."""
        data = self.curve.getData()
        if data[0] is None or data[1] is None:
            empty: NDArray[np.float64] = np.empty(0, dtype=np.float64)
            return empty, empty
        return (
            np.asarray(data[0], dtype=np.float64),
            np.asarray(data[1], dtype=np.float64),
        )
