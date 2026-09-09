"""Tek/çok kanallı grafik paneli — `F1-031`, `F3-014`.

Mockup bölge 3'ün en küçük hâli: bir kanalın zaman serisi, eksen etiketleri ve
birimiyle. PyQtGraph doğrudan kullanılmaz; bu sınıf **soyutlama sınırıdır**
(ADR-002): dışarısı yalnız `DataChunk` ve `ChannelMetadata` görür, PyQtGraph
nesneleri sızmaz.

Zaman ekseni kayıt başlangıcına göre **saniye** cinsindendir. Kanonik `int64`
nanosaniye çizim için doğrudan kullanılamaz: `float32`/`float64`'e çevrildiğinde
mutlak epoch değeri çözünürlüğü yiyor. Bu yüzden panel bir `t0` ankoru tutar ve
görece saniyeye çevirir. `t0`, grafikteki İLK seriden alınır ve tüm seriler
paylaşır — birden fazla kanal aynı eksende **karşılaştırılabilir** kalsın diye.

`F3-014`: panel artık **birden fazla seriyi aynı anda** tutabilir
(`add_channel`), her biri kendi legend girdisiyle. `remove_channel()` yalnız
hedef seriyi ve legend girdisini kaldırır; diğer seriler dokunulmadan kalır.
`set_channel()` (F1-031'in özgün API'si) geriye dönük uyumluluk için
korunuyor: tüm serileri temizleyip TEK bu kanalı ekler.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import NS_PER_SECOND
from sonar_analyzer.ui.drag_drop import CHANNEL_MIME_TYPE, decode_channel_id
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
    """Bir veya daha fazla kanalı aynı zaman ekseninde çizen panel."""

    #: F3-015: Data Explorer'dan sürüklenip bırakılan kanalın kimliği.
    #: `MainWindow` bunu dinleyip gerçek veriyi `add_channel()`'a iletir —
    #: panel kendisi repository'ye erişmez (ADR-002 soyutlama sınırı).
    channel_dropped = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plot_panel")

        #: kanal kimliği -> (metadata, eğri). Ekleme sırası korunur (dict, py3.7+).
        self._series: dict[str, tuple[ChannelMetadata, pg.PlotDataItem]] = {}
        #: `channel`/`sample_count`/`curve_data()` (parametresiz) için "birincil" seri.
        self._primary_id: str | None = None
        self._t0_ns: int | None = None

        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget(parent=self)
        self.plot.setObjectName("plot_widget")
        self.plot.setBackground(DARK.surface)
        self.plot.showGrid(x=True, y=True, alpha=GRID_ALPHA)
        self.plot.setLabel("bottom", TIME_AXIS_LABEL, units=TIME_AXIS_UNIT)
        self.plot.setTitle(EMPTY_TITLE, color=DARK.text_secondary)
        # addLegend() PLOT() cagrilarindan ONCE kurulmali; sonraki her
        # plot(..., name=...) legend'e otomatik eklenir (pyqtgraph davranisi).
        self._legend = self.plot.addLegend()

        # F3-015: grafik kanal-ağacından sürükle-bırak hedefidir.
        self.plot.setAcceptDrops(True)
        self.plot.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """`self.plot` üzerindeki sürükle-bırak olaylarını yakalar — `F3-015`.

        Yalnız geçerli `CHANNEL_MIME_TYPE` taşıyan sürüklemeler kabul edilir;
        diğerleri (örn. dosya sürükleme) dokunulmadan üst sınıfa bırakılır.
        """
        if watched is self.plot:
            if event.type() == QEvent.Type.DragEnter:
                assert isinstance(event, QDragEnterEvent)
                if event.mimeData().hasFormat(CHANNEL_MIME_TYPE):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                assert isinstance(event, QDropEvent)
                mime = event.mimeData()
                if mime.hasFormat(CHANNEL_MIME_TYPE):
                    channel_id = decode_channel_id(bytes(mime.data(CHANNEL_MIME_TYPE).data()))
                    event.acceptProposedAction()
                    self.channel_dropped.emit(channel_id)
                    return True
        return super().eventFilter(watched, event)

    # -- veri ------------------------------------------------------------

    def set_channel(self, channel: ChannelMetadata, chunk: DataChunk) -> None:
        """Grafiği **tek** bu kanala sıfırlar — `F1-031`'in özgün davranışı.

        Önceki tüm seriler (varsa) kaldırılır. Birden fazla kanalı bir
        arada tutmak için `add_channel()` kullanılır (`F3-014`).
        """
        self.clear()
        self.add_channel(channel, chunk)

    def add_channel(self, channel: ChannelMetadata, chunk: DataChunk) -> None:
        """Grafiğe bir seri ekler/günceller; **var olan diğer seriler korunur** — `F3-014`.

        Aynı `channel.id` zaten grafikteyse verisi yerinde güncellenir
        (idempotent, legend'de ikinci bir girdi açılmaz). Zaman ekseni
        (`t0`) grafikteki ilk seriden alınır; sonraki seriler aynı ankoru
        paylaşır.
        """
        if chunk.channel_id != channel.id:
            raise ValueError(
                f"Veri baska kanala ait: parca {chunk.channel_id!r}, kanal {channel.id!r}"
            )

        if self._t0_ns is None:
            self._t0_ns = chunk.start_ns or 0

        seconds = to_seconds(chunk.timestamps_ns, self._t0_ns)
        values = np.asarray(chunk.values, dtype=np.float64)
        color = channel_color(channel.id)

        existing = self._series.get(channel.id)
        if existing is not None:
            _previous_channel, curve = existing
            curve.setPen(pg.mkPen(color, width=1))
            curve.setData(seconds, values)
        else:
            curve = self.plot.plot(
                seconds, values, pen=pg.mkPen(color, width=1), name=channel.display_label
            )

        self._series[channel.id] = (channel, curve)
        if self._primary_id is None:
            self._primary_id = channel.id

        self._refresh_labels()
        self.plot.enableAutoRange()

    def remove_channel(self, channel_id: str) -> None:
        """Bir seriyi ve legend girdisini kaldırır — `F3-014`.

        Kabul kriteri: seri ve legend temizlenir; diğer seriler korunur.
        Bilinmeyen `channel_id` sessizce yok sayılır (çağıran taraf zaten
        kaldırılmış bir kanalı iki kez kaldırmaya çalışabilir).
        """
        entry = self._series.pop(channel_id, None)
        if entry is None:
            return
        _channel, curve = entry
        self.plot.removeItem(curve)
        self._legend.removeItem(curve)

        if self._primary_id == channel_id:
            self._primary_id = next(iter(self._series), None)
        if not self._series:
            self._t0_ns = None

        self._refresh_labels()

    def clear(self) -> None:
        """Paneli tümüyle boş duruma döndürür — tüm seriler kaldırılır."""
        for channel_id in list(self._series):
            self.remove_channel(channel_id)

    def _refresh_labels(self) -> None:
        """Başlık ve sol eksen etiketini şu anki seri sayısına göre günceller.

        Tek seri: kanalın adı/birimi (F1-031'deki özgün davranış). Birden
        fazla seri: farklı birimler tek eksende yanlış anlaşılmasın diye
        sol eksen etiketlenmez; başlık kaç kanal olduğunu söyler.
        """
        if not self._series:
            self.plot.setTitle(EMPTY_TITLE, color=DARK.text_secondary)
            self.plot.setLabel("left", "")
            return

        if len(self._series) == 1:
            ((channel, _curve),) = self._series.values()
            self.plot.setTitle(channel.display_label, color=DARK.text_primary)
            self.plot.setLabel("left", channel.name, units=channel.unit or "")
        else:
            self.plot.setTitle(f"{len(self._series)} kanal", color=DARK.text_primary)
            self.plot.setLabel("left", "")

        self.plot.setLabel("bottom", TIME_AXIS_LABEL, units=TIME_AXIS_UNIT)

    # -- sorgular --------------------------------------------------------

    @property
    def channel(self) -> ChannelMetadata | None:
        """Birincil kanal — ilk eklenen (veya `set_channel` ile atanan) seri."""
        if self._primary_id is None:
            return None
        return self._series[self._primary_id][0]

    @property
    def sample_count(self) -> int:
        """Birincil serinin örnek sayısı."""
        if self._primary_id is None:
            return 0
        _channel, curve = self._series[self._primary_id]
        x_data, _y_data = curve.getData()
        return 0 if x_data is None else len(x_data)

    def plotted_channel_ids(self) -> list[str]:
        """Şu an grafikte bulunan kanal kimlikleri, ekleme sırasıyla — testler için."""
        return list(self._series)

    def title_text(self) -> str:
        item = self.plot.getPlotItem().titleLabel
        return str(item.text)

    def axis_label(self, axis: str) -> str:
        """Eksenin etiket metni (birim dahil) — testler ve kabul için."""
        if axis not in ("left", "bottom"):
            raise KeyError(f"Tanimsiz eksen: {axis}")
        return str(self.plot.getPlotItem().getAxis(axis).labelString())

    def legend_labels(self) -> list[str]:
        """Legend'de görünen etiketler, ekleme sırasıyla — testler için."""
        return [channel.display_label for channel, _curve in self._series.values()]

    def curve_data(
        self, channel_id: str | None = None
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Çizilen `(zaman, değer)` dizileri.

        `channel_id` verilmezse **birincil** seri döner (`F1-031`'in tek
        parametreli özgün API'siyle geriye dönük uyumlu). Grafikte hiç
        seri yoksa veya `channel_id` bulunamazsa boş dizi çifti döner.
        """
        target_id = channel_id if channel_id is not None else self._primary_id
        if target_id is None or target_id not in self._series:
            empty: NDArray[np.float64] = np.empty(0, dtype=np.float64)
            return empty, empty

        _channel, curve = self._series[target_id]
        x_data, y_data = curve.getData()
        if x_data is None or y_data is None:
            empty = np.empty(0, dtype=np.float64)
            return empty, empty
        return np.asarray(x_data, dtype=np.float64), np.asarray(y_data, dtype=np.float64)
