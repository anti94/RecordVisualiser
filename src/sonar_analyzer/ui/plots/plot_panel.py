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

`F3-019`: **ortak zaman ekseni** sözleşmesi açık hâle getirildi. Tüm
seriler tek bir `t0` ankorunu (grafiğe ilk eklenen serinin başlangıcı)
paylaşır; her damga kanonik UTC epoch nanosaniyedir (`ADR-003`), bu
yüzden **aynı mutlak ana denk gelen iki örnek — kanal, kayıt, örnekleme
hızı ya da parça başlangıcı ne olursa olsun — aynı X koordinatına
düşer**. `x_for_timestamp_ns()` / `timestamp_ns_for_x()` bu eşlemeyi
dışarıya verir (cursor, ROI ve pan işleri bunun üstüne kurulur).

`F3-020`: **ikinci (sağ) Y ekseni**. İlk serinin birimi sol ekseni
sahiplenir; farklı birimli seriler sağ eksene (ayrı bir `ViewBox`)
gider ve o eksen birimiyle etiketlenir. Böylece `bar` ve `°C` gibi
ölçekleri çok farklı seriler aynı grafikte doğru okunur. Sağ eksen
yalnız gerektiğinde (ikinci bir birim geldiğinde) görünür olur;
grafik tek birime dönerse yine gizlenir.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPen
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

#: `F3-022`–`F3-024` yakınlaştırma kipleri: yalnız X, yalnız Y, iki eksen.
ZOOM_MODES: tuple[str, ...] = ("x", "y", "xy")
DEFAULT_ZOOM_MODE = "xy"

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

        # F3-020: iki Y ekseni. Sol eksen ilk serinin birimini sahiplenir;
        # farkli birimli seriler sag eksene (ayri ViewBox) gider.
        self._left_unit: str | None = None
        self._right_unit: str | None = None
        self._right_vb: pg.ViewBox | None = None
        #: kanal kimliği -> "left" | "right".
        self._axis_of: dict[str, str] = {}

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

        # F3-021: sürükleyerek pan. Sol tık sürükleme görünür aralığı
        # kaydırır (veriyi DEĞİL); tekerlek yakınlaştırır. pyqtgraph'ın
        # öntanımlısı zaten budur, ama açıkça sabitliyoruz.
        view_box = self.plot.getViewBox()
        view_box.setMouseMode(pg.ViewBox.PanMode)
        view_box.setMouseEnabled(x=True, y=True)

        # F3-022–F3-024: yakınlaştırma kipi. "xy" (öntanımlı) iki ekseni
        # birlikte ölçekler; "x"/"y" yalnız o ekseni — fare tekerleği ve
        # programatik `zoom()` bu kipe uyar, öteki eksen sabit kalır.
        self._zoom_mode = DEFAULT_ZOOM_MODE

        # F3-025: `reset_view()` için "ev" görünümü — veri her
        # değiştiğinde yeniden yakalanır.
        self._home_range: tuple[float, float, float, float] | None = None
        self._home_right_y: tuple[float, float] | None = None

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
        pen = pg.mkPen(color, width=1)

        existing = self._series.get(channel.id)
        if existing is not None:
            _previous_channel, curve = existing
            curve.setPen(pen)
            curve.setData(seconds, values)
        else:
            axis = self._axis_for_unit(channel.unit or "")
            curve = self._new_curve(seconds, values, pen, channel.display_label, axis)
            self._axis_of[channel.id] = axis

        self._series[channel.id] = (channel, curve)
        if self._primary_id is None:
            self._primary_id = channel.id

        self._refresh_labels()
        self._autorange()
        # F3-025: "ev" aralığı = veri her değiştiğinde yeniden sığdırılan
        # görünüm. `reset_view()` pan/zoom sonrası buraya döner.
        self._capture_home_range()

    # -- iki Y ekseni (F3-020) ----------------------------------------

    def _axis_for_unit(self, unit: str) -> str:
        """Bu birim hangi eksene düşer? İlk birim sola; ilk **farklı** birim sağa."""
        if self._left_unit is None:
            self._left_unit = unit
            return "left"
        if unit == self._left_unit:
            return "left"
        if self._right_unit is None:
            self._right_unit = unit
        return "right"

    def _new_curve(
        self,
        seconds: NDArray[np.float64],
        values: NDArray[np.float64],
        pen: QPen,
        name: str,
        axis: str,
    ) -> pg.PlotDataItem:
        if axis == "left":
            return self.plot.plot(seconds, values, pen=pen, name=name)
        self._ensure_right_axis()
        curve = pg.PlotDataItem(seconds, values, pen=pen, name=name)
        assert self._right_vb is not None
        self._right_vb.addItem(curve)
        self._legend.addItem(curve, name)
        return curve

    def _ensure_right_axis(self) -> None:
        if self._right_vb is not None:
            return
        plot_item = self.plot.getPlotItem()
        right_vb = pg.ViewBox()
        plot_item.showAxis("right")
        plot_item.scene().addItem(right_vb)
        plot_item.getAxis("right").linkToView(right_vb)
        right_vb.setXLink(plot_item)
        self._right_vb = right_vb
        self._sync_right_geometry()
        plot_item.vb.sigResized.connect(self._sync_right_geometry)

    def _sync_right_geometry(self) -> None:
        if self._right_vb is None:
            return
        plot_item = self.plot.getPlotItem()
        self._right_vb.setGeometry(plot_item.vb.sceneBoundingRect())
        self._right_vb.linkedViewChanged(plot_item.vb, self._right_vb.XAxis)

    def _teardown_right_axis(self) -> None:
        if self._right_vb is None:
            return
        plot_item = self.plot.getPlotItem()
        plot_item.vb.sigResized.disconnect(self._sync_right_geometry)
        plot_item.scene().removeItem(self._right_vb)
        plot_item.hideAxis("right")
        self._right_vb = None
        self._right_unit = None

    def _autorange(self) -> None:
        self.plot.enableAutoRange()
        if self._right_vb is not None:
            self._right_vb.enableAutoRange(axis=pg.ViewBox.YAxis)

    # -- autoscale / gorunum sifirlama (F3-025) ----------------------

    def _capture_home_range(self) -> None:
        """Verinin şu anki tam görünümünü `reset_view()` için saklar."""
        view_box = self.plot.getViewBox()
        view_box.autoRange(padding=0.05)
        self._home_range = self.visible_range()
        self._home_right_y = self.right_axis_y_range()

    def autoscale(self) -> None:
        """Görünümü **tüm veriye** sığdırır ve otomatik-aralığı açık bırakır — `F3-025`.

        Veri sonradan değişse de görünüm sığmayı sürdürür (pyqtgraph
        auto-range). Grafikte seri yoksa etkisizdir.
        """
        if not self._series:
            return
        view_box = self.plot.getViewBox()
        # autoRange() hemen sığdırır ama tek seferliktir (bayrağı kapatır);
        # ardından enableAutoRange() ile veri değiştikçe sığmayı sürdürsün.
        view_box.autoRange(padding=0.05)
        view_box.enableAutoRange(x=True, y=True)
        if self._right_vb is not None:
            self._right_vb.autoRange(padding=0.05)
            self._right_vb.enableAutoRange(axis=pg.ViewBox.YAxis)

    def reset_view(self) -> None:
        """Pan/zoom sonrası **ilk (ev) aralığa** döner — `F3-025`.

        Ev aralığı, veri en son eklendiğinde/değiştiğinde sığdırılan
        görünümdür; sabittir (autoscale gibi veriyi izlemez). Grafikte
        seri yoksa etkisizdir.
        """
        if self._home_range is None or not self._series:
            return
        x_min, x_max, y_min, y_max = self._home_range
        self.plot.getViewBox().setRange(xRange=(x_min, x_max), yRange=(y_min, y_max), padding=0)
        if self._right_vb is not None and self._home_right_y is not None:
            r_min, r_max = self._home_right_y
            self._right_vb.setRange(yRange=(r_min, r_max), padding=0)

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
        if self._axis_of.pop(channel_id, "left") == "right" and self._right_vb is not None:
            self._right_vb.removeItem(curve)
        else:
            self.plot.removeItem(curve)
        self._legend.removeItem(curve)

        if self._primary_id == channel_id:
            self._primary_id = next(iter(self._series), None)
        if "right" not in self._axis_of.values():
            self._teardown_right_axis()
        if not self._series:
            self._t0_ns = None
            self._left_unit = None
            self._home_range = None
            self._home_right_y = None
        else:
            self._capture_home_range()

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
            # F3-020: birimler eksende. Tek birim varsa sol eksene yazılır;
            # ikinci birim varsa sağ eksene (kendi ViewBox'ında) yazılır.
            self.plot.setLabel("left", "", units=self._left_unit or "")
        if self._right_vb is not None and self._right_unit:
            self.plot.getPlotItem().getAxis("right").setLabel("", units=self._right_unit)

        self.plot.setLabel("bottom", TIME_AXIS_LABEL, units=TIME_AXIS_UNIT)

    # -- ortak zaman ekseni (F3-019) -----------------------------------

    @property
    def time_anchor_ns(self) -> int | None:
        """X=0'a denk gelen mutlak UTC epoch nanosaniye; seri yoksa `None`.

        Ankor grafiğe **ilk eklenen** seriden alınır ve tüm seriler
        paylaşır; sonradan o seri kaldırılsa bile (grafik boşalana dek)
        değişmez — eksen kayıp gitmesin diye.
        """
        return self._t0_ns

    def x_for_timestamp_ns(self, timestamp_ns: int) -> float:
        """Mutlak epoch-ns bir anı grafiğin X koordinatına (saniye) çevirir — `F3-019`.

        Ortak ankoru kullanır, dolayısıyla **hangi kanala ait olduğu fark
        etmez**: aynı `timestamp_ns` her seride aynı X'i verir. Henüz seri
        yoksa (`ankor None`) `RuntimeError`.
        """
        if self._t0_ns is None:
            raise RuntimeError("Zaman ekseni ankoru yok: once bir kanal ekleyin.")
        return (timestamp_ns - self._t0_ns) / NS_PER_SECOND

    def timestamp_ns_for_x(self, x_seconds: float) -> int:
        """`x_for_timestamp_ns`'in tersi: X (saniye) -> mutlak epoch-ns — `F3-019`."""
        if self._t0_ns is None:
            raise RuntimeError("Zaman ekseni ankoru yok: once bir kanal ekleyin.")
        return self._t0_ns + round(x_seconds * NS_PER_SECOND)

    # -- pan / gorunur aralik (F3-021) --------------------------------

    def pan(self, dx: float, dy: float = 0.0) -> None:
        """Görünür aralığı `dx` saniye / `dy` birim kaydırır — `F3-021`.

        Yalnız **görünümü** taşır; seri verisine (eğri dizileri, kaynak
        `DataChunk`) dokunmaz. Fare sürüklemesinin programatik karşılığı;
        pan sonrası autorange kapanır (pyqtgraph davranışı).
        """
        self.plot.getViewBox().translateBy(x=dx, y=dy)

    def visible_range(self) -> tuple[float, float, float, float]:
        """Görünür `(x_min, x_max, y_min, y_max)` — saniye / sol eksen birimi."""
        (x_min, x_max), (y_min, y_max) = self.plot.getViewBox().viewRange()
        return float(x_min), float(x_max), float(y_min), float(y_max)

    def visible_x_range(self) -> tuple[float, float]:
        """Görünür zaman aralığı `(x_min, x_max)` saniye."""
        x_min, x_max, _y_min, _y_max = self.visible_range()
        return x_min, x_max

    def right_axis_y_range(self) -> tuple[float, float] | None:
        """İkinci (sağ) Y ekseninin görünür `(y_min, y_max)` aralığı; yoksa `None` — `F3-020`."""
        if self._right_vb is None:
            return None
        (_x0, _x1), (y_min, y_max) = self._right_vb.viewRange()
        return float(y_min), float(y_max)

    # -- yakinlastirma kipi (F3-022 / F3-023 / F3-024) ---------------

    @property
    def zoom_mode(self) -> str:
        """Etkin yakınlaştırma kipi: `"x"`, `"y"` ya da `"xy"`."""
        return self._zoom_mode

    def set_zoom_mode(self, mode: str) -> None:
        """Yakınlaştırma kipini değiştirir — `F3-022`–`F3-024`.

        Kip, hem fare tekerleğini hem programatik `zoom()`'u etkiler:
        `"x"` kipinde Y ekseni (aralığı ve etkileşimi) dokunulmadan
        kalır, `"y"` kipinde X. Pan da aynı eksen kısıtına uyar —
        "yalnız X" gerçekten yalnız X demektir.
        """
        if mode not in ZOOM_MODES:
            raise ValueError(f"Bilinmeyen yakinlastirma kipi: {mode!r}")
        self._zoom_mode = mode
        self.plot.getViewBox().setMouseEnabled(x=mode in ("x", "xy"), y=mode in ("y", "xy"))

    def zoom(self, factor: float) -> None:
        """Görünür aralığı etkin kipin eksen(ler)inde `factor` kadar ölçekler.

        `factor < 1` yakınlaşır (aralık daralır), `factor > 1` uzaklaşır.
        Ölçekleme görünür alanın merkezine göredir; **veri değişmez**.
        """
        if factor <= 0:
            raise ValueError(f"Olcek pozitif olmali: {factor}")
        sx = factor if self._zoom_mode in ("x", "xy") else 1.0
        sy = factor if self._zoom_mode in ("y", "xy") else 1.0
        self.plot.getViewBox().scaleBy(x=sx, y=sy)
        # F3-020 ikinci Y ekseni: X'e bağlı ama Y'si bağımsız — Y
        # yakınlaştırmasında onu da aynı oranda ölçekle ki iki eksen
        # tutarlı kalsın.
        if self._right_vb is not None and sy != 1.0:
            self._right_vb.scaleBy(y=sy)

    def zoom_to_region(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        """Görünümü seçilen `(x, y)` dikdörtgenine yakınlaştırır — `F3-024`.

        Kullanıcının sürükleyerek seçtiği bölgenin programatik karşılığı:
        **iki eksen birden** verilen sınırlara oturur (kip fark etmez —
        bölge seçimi tanımı gereği iki eksenlidir). Kenarlar artan sırada
        olmalı; değilse `ValueError`. Görünüm değişir, **veri değişmez**.
        """
        if x_min >= x_max or y_min >= y_max:
            raise ValueError(
                f"Gecersiz bolge: x=({x_min}, {x_max}), y=({y_min}, {y_max}) "
                "— kenarlar artan sirada olmali."
            )
        self.plot.getViewBox().setRange(xRange=(x_min, x_max), yRange=(y_min, y_max), padding=0)

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
        if axis not in ("left", "right", "bottom"):
            raise KeyError(f"Tanimsiz eksen: {axis}")
        return str(self.plot.getPlotItem().getAxis(axis).labelString())

    def axis_for_channel(self, channel_id: str) -> str:
        """Serinin çizildiği Y ekseni: `"left"` | `"right"` — `F3-020`."""
        if channel_id not in self._series:
            raise KeyError(f"Grafikte yok: {channel_id}")
        return self._axis_of.get(channel_id, "left")

    @property
    def right_axis_visible(self) -> bool:
        """Sağ Y ekseni (ikinci birim) şu an gösteriliyor mu — `F3-020`."""
        return self._right_vb is not None

    @property
    def left_unit(self) -> str | None:
        """Sol Y ekseninin sahiplendiği birim; seri yoksa `None`."""
        return self._left_unit

    @property
    def right_unit(self) -> str | None:
        """Sağ Y eksenine atanmış birim; ikinci birim yoksa `None`."""
        return self._right_unit

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
