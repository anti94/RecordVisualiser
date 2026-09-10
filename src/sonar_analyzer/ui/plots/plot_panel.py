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

import contextlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import NS_PER_SECOND, TimeRange
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


#: `F3-031` çizgi biçimleri -> Qt kalem stili.
LINE_STYLES: dict[str, Qt.PenStyle] = {
    "solid": Qt.PenStyle.SolidLine,
    "dash": Qt.PenStyle.DashLine,
    "dot": Qt.PenStyle.DotLine,
    "none": Qt.PenStyle.NoPen,
}
#: `F3-031` desteklenen pyqtgraph marker sembolleri (`None` = marker yok).
SERIES_SYMBOLS: tuple[str, ...] = ("o", "s", "t", "d", "+", "x")


@dataclass(frozen=True)
class SeriesStyle:
    """Bir serinin çizim biçimi — `F3-031`.

    `color`: `#rrggbb`. `width`: çizgi kalınlığı (px). `line_style`:
    `LINE_STYLES` anahtarı. `symbol`: `SERIES_SYMBOLS`'tan biri ya da
    `None`.
    """

    color: str
    width: int = 1
    line_style: str = "solid"
    symbol: str | None = None


@dataclass(frozen=True)
class DeltaReading:
    """İki ölçüm cursoru (A→B) arasındaki fark — `F3-027`.

    `dt_seconds` ve `dvalue` işaretlidir (B − A). `frequency_hz`, `dt`
    sıfır değilse `1 / |dt|`, sıfırsa `None` (sıfıra bölme yok).
    """

    dt_seconds: float
    dvalue: float
    frequency_hz: float | None


def to_seconds(timestamps_ns: NDArray[np.int64], t0_ns: int) -> NDArray[np.float64]:
    """Nanosaniye damgalarını `t0`'a göre saniyeye çevirir."""
    return (timestamps_ns - t0_ns).astype(np.float64) / NS_PER_SECOND


class PlotPanel(QWidget):
    """Bir veya daha fazla kanalı aynı zaman ekseninde çizen panel."""

    #: F3-015: Data Explorer'dan sürüklenip bırakılan kanalın kimliği.
    #: `MainWindow` bunu dinleyip gerçek veriyi `add_channel()`'a iletir —
    #: panel kendisi repository'ye erişmez (ADR-002 soyutlama sınırı).
    channel_dropped = Signal(str)
    #: F3-026: crosshair hareket etti — (cursor zamanı [s], birincil seride
    #: en yakın örnek değeri). Yakında örnek yoksa yayılmaz.
    cursor_moved = Signal(float, float)
    #: F3-028: zaman bölgesi seçildi/değişti — (start_ns, end_ns) mutlak
    #: UTC epoch nanosaniye; `MainWindow` bunu repository sorgusuna verir.
    #: `object`: epoch-ns değerleri C++ 32-bit `int`'e sığmaz, Python int
    #: olarak taşınır.
    time_region_changed = Signal(object, object)
    #: F3-032: görünür X aralığı KULLANICI gezinmesiyle değişti — (x_min,
    #: x_max) saniye. `apply_x_range()` ile gelen dış güncellemede yayılmaz
    #: (döngü önleme).
    x_range_changed = Signal(float, float)

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
        #: F3-031: kanal kimliği -> çizim biçimi (varsayılan ya da geçersiz kılma).
        self._styles: dict[str, SeriesStyle] = {}

        # F3-030: legend'den seri gizleme + solo. `solo` etkinken yalnız
        # bir seri görünür; kapatınca solo ÖNCESİ görünürlükler geri gelir.
        self._solo_id: str | None = None
        self._pre_solo_visibility: dict[str, bool] | None = None

        # F3-032: paneller arası X senkronizasyonu. Dıştan gelen aralık
        # uygulanırken bu bayrak açılır ki `x_range_changed` yeniden
        # yayılmasın (geri besleme döngüsü olmaz).
        self._suppress_x_broadcast = False

        # F3-045: olay zaman işaretleri. (timestamp_ns, renk) çiftleri
        # saklanır; her biri X ekseninde `x_for_timestamp_ns` ile
        # konumlanan bir dikey çizgiye dönüşür.
        self._event_marks: list[tuple[int, str]] = []
        self._event_lines: list[pg.InfiniteLine] = []
        self._event_markers_visible = True

        # F3-047: TX (transmisyon) aralıkları — (start_ns, end_ns) çiftleri
        # gölgeli bant olarak çizilir; START/STOP sınırları zaman ekseniyle
        # eşleşir.
        self._tx_spans: list[tuple[int, int]] = []
        self._tx_regions: list[pg.LinearRegionItem] = []
        self._tx_regions_visible = True

        #: F3-034: `dispose()` çağrıldı mı — ikinci çağrı sessizce döner.
        self._disposed = False

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

        # F3-026: fareyi izleyen crosshair + en yakın örnek okuması.
        self._cursor_x: float | None = None
        self._vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(DARK.text_secondary))
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(DARK.text_secondary))
        for line in (self._vline, self._hline):
            line.setVisible(False)
            self.plot.addItem(line, ignoreBounds=True)
        self._cursor_text = ""
        self.plot.scene().sigMouseMoved.connect(self._on_scene_mouse_moved)

        # F3-027: iki ölçüm cursoru (A, B) — en yakın örneğe kenetlenir;
        # aralarındaki Δt / Δdeğer / frekans raporlanır.
        self._cursor_a: tuple[float, float] | None = None
        self._cursor_b: tuple[float, float] | None = None
        _delta_pen = pg.mkPen(DARK.text_primary, style=Qt.PenStyle.DashLine)
        self._aline = pg.InfiniteLine(angle=90, movable=False, pen=_delta_pen, label="A")
        self._bline = pg.InfiniteLine(angle=90, movable=False, pen=_delta_pen, label="B")
        for line in (self._aline, self._bline):
            line.setVisible(False)
            self.plot.addItem(line, ignoreBounds=True)
        self._delta_text = ""

        # F3-028: zaman bölgesi (ROI) seçimi — sürüklenebilir bant;
        # seçili [x0, x1] mutlak epoch-ns TimeRange'e dönüşür.
        self._region = pg.LinearRegionItem(orientation="vertical")
        self._region.setVisible(False)
        self._region.setZValue(-5)
        self.plot.addItem(self._region, ignoreBounds=True)
        self._region_active = False
        self._region.sigRegionChangeFinished.connect(self._emit_time_region)

        # F3-032: X aralığı değişince yayınla (dış güncelleme değilse).
        view_box.sigXRangeChanged.connect(self._on_x_range_changed)

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

        existing = self._series.get(channel.id)
        if existing is not None:
            _previous_channel, curve = existing
            curve.setData(seconds, values)
        else:
            # F3-031: yeni seri kanal kimliğinden türeyen KALICI varsayılan
            # renkle başlar — aynı kanal her panelde aynı renkte açılır.
            self._styles[channel.id] = SeriesStyle(color=channel_color(channel.id))
            axis = self._axis_for_unit(channel.unit or "")
            curve = self._new_curve(
                seconds,
                values,
                pg.mkPen(self._styles[channel.id].color, width=1),
                channel.display_label,
                axis,
            )
            self._axis_of[channel.id] = axis
            # F3-030: solo etkinken eklenen yeni seri gizli başlar; solo
            # kapanınca görünür olması için ön-görünürlüğe kaydedilir.
            if self._solo_id is not None and channel.id != self._solo_id:
                curve.setVisible(False)
                if self._pre_solo_visibility is not None:
                    self._pre_solo_visibility[channel.id] = True

        self._series[channel.id] = (channel, curve)
        # F3-031: saklanan stil (varsayılan ya da kullanıcı geçersiz kılması)
        # her ekleme/güncellemede yeniden uygulanır.
        self._apply_style(channel.id)
        if self._primary_id is None:
            self._primary_id = channel.id

        self._refresh_labels()
        self._autorange()
        # F3-025: "ev" aralığı = veri her değiştiğinde yeniden sığdırılan
        # görünüm. `reset_view()` pan/zoom sonrası buraya döner.
        self._capture_home_range()
        # F3-045: ilk seri ankoru verince bekleyen olay işaretleri yerleşir.
        self._rebuild_event_markers()
        self._rebuild_tx_regions()

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

    # -- crosshair / cursor okumasi (F3-026) ------------------------

    def _on_scene_mouse_moved(self, scene_pos: object) -> None:
        """Fare grafiğin üstündeyken crosshair'i taşır; dışına çıkınca gizler."""
        vb = self.plot.getViewBox()
        if not self.plot.sceneBoundingRect().contains(scene_pos):
            self.clear_cursor()
            return
        point = vb.mapSceneToView(scene_pos)
        self.set_cursor(float(point.x()), float(point.y()))

    def set_cursor(self, x_seconds: float, y_value: float | None = None) -> None:
        """Crosshair'i `x_seconds`'e (ve verilirse `y_value`'ya) taşır — `F3-026`.

        Fare hareketinin programatik karşılığı. Dikey çizgi zamanı,
        yatay çizgi (varsa) imlecin Y'sini gösterir; okuma metni birincil
        seride **en yakın örneğe** göre hesaplanır ve `cursor_moved`
        yayılır. Grafikte seri yoksa etkisizdir.
        """
        if not self._series:
            return
        self._cursor_x = x_seconds
        self._vline.setPos(x_seconds)
        self._vline.setVisible(True)
        if y_value is not None:
            self._hline.setPos(y_value)
            self._hline.setVisible(True)

        nearest = self.nearest_sample(x_seconds)
        if nearest is None:
            self._cursor_text = f"t={x_seconds:.3f} s"
            return
        sample_t, sample_v = nearest
        primary = self.channel
        unit = f" {primary.unit}" if primary and primary.unit else ""
        label = primary.name if primary else "deger"
        self._cursor_text = f"t={sample_t:.3f} s  |  {label}: {sample_v:.4g}{unit}"
        self.cursor_moved.emit(sample_t, sample_v)

    def clear_cursor(self) -> None:
        """Crosshair'i gizler ve okuma metnini temizler — `F3-026`."""
        self._cursor_x = None
        self._cursor_text = ""
        self._vline.setVisible(False)
        self._hline.setVisible(False)

    def cursor_x(self) -> float | None:
        """Crosshair'in şu anki zaman konumu (saniye); yoksa `None`."""
        return self._cursor_x

    def cursor_readout_text(self) -> str:
        """Cursor okuması: zaman ve en yakın örnek değeri — boşsa `""`."""
        return self._cursor_text

    def nearest_sample(
        self, x_seconds: float, channel_id: str | None = None
    ) -> tuple[float, float] | None:
        """`x_seconds`'e en yakın örneğin `(zaman_s, deger)` çiftini döndürür — `F3-026`.

        `channel_id` verilmezse birincil seri. Seri yoksa/boşsa `None`.
        """
        x_data, y_data = self.curve_data(channel_id)
        if x_data.size == 0:
            return None
        idx = int(np.argmin(np.abs(x_data - x_seconds)))
        return float(x_data[idx]), float(y_data[idx])

    def crosshair_visible(self) -> bool:
        """Dikey crosshair çizgisi şu an görünüyor mu — testler için."""
        return bool(self._vline.isVisible())

    # -- iki cursor fark olcumu (F3-027) --------------------------

    def set_cursor_a(self, x_seconds: float) -> None:
        """A ölçüm cursorunu `x_seconds`'e en yakın örneğe kenetler — `F3-027`."""
        self._cursor_a = self._place_delta_cursor(self._aline, x_seconds)
        self._refresh_delta_text()

    def set_cursor_b(self, x_seconds: float) -> None:
        """B ölçüm cursorunu `x_seconds`'e en yakın örneğe kenetler — `F3-027`."""
        self._cursor_b = self._place_delta_cursor(self._bline, x_seconds)
        self._refresh_delta_text()

    def _place_delta_cursor(
        self, line: pg.InfiniteLine, x_seconds: float
    ) -> tuple[float, float] | None:
        nearest = self.nearest_sample(x_seconds)
        if nearest is None:
            line.setVisible(False)
            return None
        sample_t, _sample_v = nearest
        line.setPos(sample_t)
        line.setVisible(True)
        return nearest

    def clear_delta_cursors(self) -> None:
        """A ve B ölçüm cursorlarını kaldırır — `F3-027`."""
        self._cursor_a = None
        self._cursor_b = None
        self._delta_text = ""
        self._aline.setVisible(False)
        self._bline.setVisible(False)

    def cursor_a_x(self) -> float | None:
        """A cursorunun kenetlendiği örnek zamanı (saniye); yoksa `None`."""
        return None if self._cursor_a is None else self._cursor_a[0]

    def cursor_b_x(self) -> float | None:
        """B cursorunun kenetlendiği örnek zamanı (saniye); yoksa `None`."""
        return None if self._cursor_b is None else self._cursor_b[0]

    def delta_measurement(self) -> DeltaReading | None:
        """A→B farkı; iki cursor da yerleştirilmemişse `None` — `F3-027`.

        `dt`/`dvalue` işaretlidir (B − A). Frekans yalnız `dt != 0` iken
        `1 / |dt|`, aksi hâlde `None`.
        """
        if self._cursor_a is None or self._cursor_b is None:
            return None
        a_t, a_v = self._cursor_a
        b_t, b_v = self._cursor_b
        dt = b_t - a_t
        frequency = 1.0 / abs(dt) if dt != 0.0 else None
        return DeltaReading(dt_seconds=dt, dvalue=b_v - a_v, frequency_hz=frequency)

    def delta_readout_text(self) -> str:
        """Δt / Δdeğer / frekans okuması — iki cursor yoksa `""`."""
        return self._delta_text

    def _refresh_delta_text(self) -> None:
        reading = self.delta_measurement()
        if reading is None:
            self._delta_text = ""
            return
        primary = self.channel
        unit = f" {primary.unit}" if primary and primary.unit else ""
        parts = [
            f"Δt={reading.dt_seconds:.3f} s",
            f"Δ={reading.dvalue:.4g}{unit}",
        ]
        if reading.frequency_hz is not None:
            parts.append(f"f={reading.frequency_hz:.4g} Hz")
        self._delta_text = "  |  ".join(parts)

    # -- zaman bolgesi secimi (F3-028) ---------------------------

    def set_time_region(self, x_start: float, x_end: float) -> None:
        """Zaman bölgesini `[min, max]` saniye aralığına kurar/gösterir — `F3-028`.

        Kenarlar herhangi bir sırada verilebilir; normalize edilir.
        Grafikte seri yoksa (zaman ankoru yok) etkisizdir.
        """
        if self._t0_ns is None:
            return
        lo, hi = sorted((x_start, x_end))
        self._region_active = True
        self._region.setVisible(True)
        self._region.setRegion((lo, hi))  # sigRegionChangeFinished -> _emit_time_region

    def clear_time_region(self) -> None:
        """Zaman bölgesi seçimini kaldırır — `F3-028`."""
        self._region_active = False
        self._region.setVisible(False)

    def time_region_x(self) -> tuple[float, float] | None:
        """Seçili bölgenin `(x_min, x_max)` saniye sınırları; seçim yoksa `None`."""
        if not self._region_active:
            return None
        lo, hi = cast("tuple[float, float]", self._region.getRegion())
        return float(lo), float(hi)

    def time_region_range(self) -> TimeRange | None:
        """Seçili bölgeyi **mutlak epoch-ns** `TimeRange`'e dönüştürür — `F3-028`.

        Kabul kriteri: seçili başlangıç/bitiş repository aralığına dönüşür.
        Seçim yoksa ya da zaman ankoru yoksa `None`.
        """
        span = self.time_region_x()
        if span is None or self._t0_ns is None:
            return None
        lo, hi = span
        return TimeRange(self.timestamp_ns_for_x(lo), self.timestamp_ns_for_x(hi))

    def _emit_time_region(self) -> None:
        time_range = self.time_region_range()
        if time_range is not None:
            self.time_region_changed.emit(time_range.start_ns, time_range.end_ns)

    def zoom_to_time_region(self, *, clear_region: bool = True) -> bool:
        """Görünümü seçili zaman bölgesine daraltır — `F3-029`.

        Kabul kriteri: grafik **yalnız** seçilen zaman aralığını gösterir.
        X ekseni tam olarak bölgeye oturur; Y (ve varsa ikinci Y) o
        pencereye düşen örneklere sığdırılır. Bölge yoksa `False` döner ve
        görünüm değişmez. `clear_region=True` (öntanımlı) işi biten bandı
        kaldırır; `reset_view()` tam görünüme geri döndürür.
        """
        span = self.time_region_x()
        if span is None:
            return False
        x_lo, x_hi = span
        view_box = self.plot.getViewBox()
        view_box.setRange(xRange=(x_lo, x_hi), padding=0)

        left_bounds = self._windowed_y_bounds(x_lo, x_hi, "left")
        if left_bounds is not None:
            view_box.setRange(yRange=left_bounds, padding=0.05)
        if self._right_vb is not None:
            right_bounds = self._windowed_y_bounds(x_lo, x_hi, "right")
            if right_bounds is not None:
                self._right_vb.setRange(yRange=right_bounds, padding=0.05)

        if clear_region:
            self.clear_time_region()
        return True

    def _windowed_y_bounds(self, x_lo: float, x_hi: float, axis: str) -> tuple[float, float] | None:
        """`[x_lo, x_hi]` penceresine düşen örneklerin Y `(min, max)`'ı; yoksa `None`."""
        lows: list[float] = []
        highs: list[float] = []
        for channel_id, (_channel, _curve) in self._series.items():
            if self._axis_of.get(channel_id, "left") != axis:
                continue
            x_data, y_data = self.curve_data(channel_id)
            if x_data.size == 0:
                continue
            mask = (x_data >= x_lo) & (x_data <= x_hi)
            windowed = y_data[mask]
            if windowed.size == 0:
                continue
            lows.append(float(windowed.min()))
            highs.append(float(windowed.max()))
        if not lows:
            return None
        return min(lows), max(highs)

    # -- olay zaman isaretleri (F3-045) -------------------------

    def set_event_markers(self, marks: Sequence[tuple[int, str]]) -> None:
        """Olay zaman işaretlerini `(timestamp_ns, renk)` çiftlerinden kurar — `F3-045`.

        Her işaret, X ekseninde `x_for_timestamp_ns` ile hesaplanan
        konuma bir dikey çizgi koyar — olay zamanı grafik X koordinatıyla
        eşleşir (kabul kriteri). Henüz seri (zaman ankoru) yoksa çiftler
        saklanır ve ilk seri eklenince yerleşir.
        """
        self._event_marks = list(marks)
        self._rebuild_event_markers()

    def clear_event_markers(self) -> None:
        """Tüm olay işaretlerini kaldırır — `F3-045`."""
        self._event_marks = []
        self._rebuild_event_markers()

    def _rebuild_event_markers(self) -> None:
        for line in self._event_lines:
            self.plot.removeItem(line)
        self._event_lines = []
        if self._t0_ns is None:
            return
        for timestamp_ns, color in self._event_marks:
            line = pg.InfiniteLine(
                pos=self.x_for_timestamp_ns(timestamp_ns),
                angle=90,
                movable=False,
                pen=pg.mkPen(color, width=1, style=Qt.PenStyle.DashLine),
            )
            line.setVisible(self._event_markers_visible)
            self.plot.addItem(line, ignoreBounds=True)
            self._event_lines.append(line)

    def set_event_markers_visible(self, visible: bool) -> None:
        """Olay işaretlerini gösterir/gizler — **veri değişmez** — `F3-050`."""
        self._event_markers_visible = visible
        for line in self._event_lines:
            line.setVisible(visible)

    @property
    def event_markers_visible(self) -> bool:
        return self._event_markers_visible

    def event_marker_count(self) -> int:
        """Şu an çizili olay işareti sayısı — testler için."""
        return len(self._event_lines)

    def event_marker_x(self, index: int) -> float:
        """`index`. olay işaretinin X konumu (saniye)."""
        return float(cast("float", self._event_lines[index].value()))

    def event_marker_times_ns(self) -> list[int]:
        """İşaretlerin mutlak epoch-ns zamanları, verildikleri sırayla."""
        return [timestamp_ns for timestamp_ns, _color in self._event_marks]

    # -- TX araliklari: golgeli bolgeler (F3-047) --------------

    def set_tx_regions(self, spans: Sequence[tuple[int, int]]) -> None:
        """TX aralıklarını `(start_ns, end_ns)` çiftlerinden gölgeli bant çizer — `F3-047`.

        Her bandın sol/sağ kenarı `x_for_timestamp_ns` ile hesaplanır —
        START/STOP sınırları zaman ekseniyle eşleşir (kabul kriteri).
        Zaman ankoru yoksa çiftler saklanır ve ilk seri eklenince yerleşir.
        """
        self._tx_spans = [(min(a, b), max(a, b)) for a, b in spans]
        self._rebuild_tx_regions()

    def clear_tx_regions(self) -> None:
        """Tüm TX bantlarını kaldırır — `F3-047`."""
        self._tx_spans = []
        self._rebuild_tx_regions()

    def _rebuild_tx_regions(self) -> None:
        for region in self._tx_regions:
            self.plot.removeItem(region)
        self._tx_regions = []
        if self._t0_ns is None:
            return
        for start_ns, end_ns in self._tx_spans:
            region = pg.LinearRegionItem(
                values=(self.x_for_timestamp_ns(start_ns), self.x_for_timestamp_ns(end_ns)),
                orientation="vertical",
                movable=False,
                brush=pg.mkBrush(120, 170, 230, 45),
            )
            region.setZValue(-10)
            region.setVisible(self._tx_regions_visible)
            self.plot.addItem(region, ignoreBounds=True)
            self._tx_regions.append(region)

    def set_tx_regions_visible(self, visible: bool) -> None:
        """TX bantlarını gösterir/gizler — **veri değişmez** — `F3-050`."""
        self._tx_regions_visible = visible
        for region in self._tx_regions:
            region.setVisible(visible)

    @property
    def tx_regions_visible(self) -> bool:
        return self._tx_regions_visible

    def tx_region_count(self) -> int:
        """Şu an çizili TX bandı sayısı — testler için."""
        return len(self._tx_regions)

    def tx_region_x(self, index: int) -> tuple[float, float]:
        """`index`. TX bandının `(x_start, x_end)` konumu (saniye)."""
        lo, hi = cast("tuple[float, float]", self._tx_regions[index].getRegion())
        return float(lo), float(hi)

    def tx_region_times_ns(self) -> list[tuple[int, int]]:
        """TX bantlarının `(start_ns, end_ns)` zamanları, verildikleri sırayla."""
        return list(self._tx_spans)

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
        self._styles.pop(channel_id, None)
        if self._axis_of.pop(channel_id, "left") == "right" and self._right_vb is not None:
            self._right_vb.removeItem(curve)
        else:
            self.plot.removeItem(curve)
        self._legend.removeItem(curve)

        if self._primary_id == channel_id:
            self._primary_id = next(iter(self._series), None)
        if "right" not in self._axis_of.values():
            self._teardown_right_axis()
        # F3-030: solo edilen seri gittiyse solo kapanır ve kalan seriler
        # solo öncesi görünürlüğüne döner; başka seri gittiyse yalnız
        # ön-görünürlük anlık görüntüsünden düşülür.
        if self._solo_id == channel_id:
            self._solo_id = None
            snapshot = self._pre_solo_visibility or {}
            for cid, (_c, other_curve) in self._series.items():
                other_curve.setVisible(snapshot.get(cid, True))
            self._pre_solo_visibility = None
        elif self._pre_solo_visibility is not None:
            self._pre_solo_visibility.pop(channel_id, None)
        if not self._series:
            self._t0_ns = None
            self._left_unit = None
            self._home_range = None
            self._home_right_y = None
            self.clear_cursor()
            self.clear_delta_cursors()
            self.clear_time_region()
            self._rebuild_event_markers()  # ankor gitti: işaretleri kaldır
            self._rebuild_tx_regions()
        else:
            self._capture_home_range()

        self._refresh_labels()

    def clear(self) -> None:
        """Paneli tümüyle boş duruma döndürür — tüm seriler kaldırılır."""
        for channel_id in list(self._series):
            self.remove_channel(channel_id)

    def dispose(self) -> None:
        """Paneli kalıcı olarak kapatır: sinyalleri koparır, veriyi bırakır — `F3-034`.

        Kapatılan panel bir daha kullanılmamalıdır. Tüm seriler (ve
        taşıdıkları `DataChunk` dizileri) bırakılır, pyqtgraph sinyal
        abonelikleri sökülür ki panel çöp toplanınca geç sinyaller
        çalışan koda dokunamasın. İki kez çağrılması güvenlidir.
        """
        if self._disposed:
            return
        self._disposed = True
        self.clear()
        self.clear_event_markers()
        self.clear_tx_regions()
        self._teardown_right_axis()
        for signal, slot in (
            (self.plot.scene().sigMouseMoved, self._on_scene_mouse_moved),
            (self._region.sigRegionChangeFinished, self._emit_time_region),
            (self.plot.getViewBox().sigXRangeChanged, self._on_x_range_changed),
        ):
            with contextlib.suppress(RuntimeError, TypeError):
                signal.disconnect(slot)
        self._styles.clear()
        self._pre_solo_visibility = None

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

    # -- paneller arasi X senkronu (F3-032) --------------------

    def set_x_range(self, x_min: float, x_max: float) -> None:
        """Görünür X aralığını kurar — kullanıcı gezinmesi sayılır — `F3-032`.

        `x_range_changed` yayılır; bağlı paneller (`XAxisLink`) izler.
        """
        self.plot.getViewBox().setXRange(x_min, x_max, padding=0)

    def apply_x_range(self, x_min: float, x_max: float) -> None:
        """Bağlı bir panelden gelen X aralığını uygular — `F3-032`.

        `x_range_changed` **yayılmaz**: aksi hâlde paneller birbirini
        sonsuza dek tetiklerdi (döngü önleme).
        """
        self._suppress_x_broadcast = True
        try:
            self.plot.getViewBox().setXRange(x_min, x_max, padding=0)
        finally:
            self._suppress_x_broadcast = False

    def _on_x_range_changed(self, _view_box: object, x_range: object) -> None:
        if self._suppress_x_broadcast or self._disposed:
            return
        lo, hi = cast("tuple[float, float]", x_range)
        self.x_range_changed.emit(float(lo), float(hi))

    def right_axis_y_range(self) -> tuple[float, float] | None:
        """İkinci (sağ) Y ekseninin görünür `(y_min, y_max)` aralığı; yoksa `None` — `F3-020`."""
        if self._right_vb is None:
            return None
        (_x0, _x1), (y_min, y_max) = self._right_vb.viewRange()
        return float(y_min), float(y_max)

    def set_axis_range(self, axis: str, y_min: float, y_max: float) -> None:
        """Bir Y ekseninin görünür aralığını elle sabitler — `F3-036`.

        `axis`: `"left"` ya da `"right"`. `"right"` yalnız ikinci eksen
        varken bir şey yapar. Kenarlar artan sırada olmalı; değilse
        `ValueError`.
        """
        if axis not in ("left", "right"):
            raise ValueError(f"Tanimsiz eksen: {axis!r}")
        if y_min >= y_max:
            raise ValueError(f"Gecersiz aralik: ({y_min}, {y_max}) — artan sirada olmali.")
        if axis == "left":
            self.plot.getViewBox().setYRange(y_min, y_max, padding=0)
        elif self._right_vb is not None:
            self._right_vb.setYRange(y_min, y_max, padding=0)

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

    def export_svg(self, path: str | Path) -> Path:
        """Grafiği **vektörel** SVG olarak yazar — `F3-063`.

        pyqtgraph'ın kendi `SVGExporter`'ı sahne grafiğini dolaşır: seriler
        `<path>`, eksen ve başlık metinleri `<text>` olarak çıkar, çıktı
        kayıpsız ölçeklenir. PyQtGraph yalnız bu adaptör katmanında görünür
        (ADR-002), bu yüzden SVG üretimi de burada durur.

        Grafikte çizili kanal yoksa `ValueError`; disk yazımı başarısızsa
        `OSError`.
        """
        from pyqtgraph.exporters import SVGExporter

        if not self._series:
            raise ValueError("Cizili kanal yok: SVG disa aktarilamaz")

        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        exporter = SVGExporter(self.plot.getPlotItem())
        exporter.export(str(dest))
        if not dest.exists() or dest.stat().st_size == 0:
            raise OSError(f"SVG yazilamadi: {dest}")
        return dest

    # -- seri gorunurlugu / solo (F3-030) -----------------------

    def set_series_visible(self, channel_id: str, visible: bool) -> None:
        """Bir serinin görünürlüğünü açar/kapatır — `F3-030`.

        Seri grafikten kaldırılmaz (`plotted_channel_ids` değişmez), yalnız
        çizgisi gizlenir. Solo etkinken yapılan değişiklik solo çıkışında
        geri alınacak duruma da yazılır.
        """
        entry = self._series.get(channel_id)
        if entry is None:
            raise KeyError(f"Grafikte yok: {channel_id}")
        entry[1].setVisible(visible)
        if self._pre_solo_visibility is not None:
            self._pre_solo_visibility[channel_id] = visible

    def is_series_visible(self, channel_id: str) -> bool:
        """Seri şu an görünür mü — `F3-030`."""
        entry = self._series.get(channel_id)
        if entry is None:
            raise KeyError(f"Grafikte yok: {channel_id}")
        return bool(entry[1].isVisible())

    def visible_channel_ids(self) -> list[str]:
        """Görünür serilerin kimlikleri, ekleme sırasıyla."""
        return [cid for cid, (_c, curve) in self._series.items() if curve.isVisible()]

    def soloed_channel(self) -> str | None:
        """Solo edilmiş kanal; solo kapalıysa `None`."""
        return self._solo_id

    def solo_series(self, channel_id: str) -> None:
        """Yalnız `channel_id`'yi gösterir, diğerlerini gizler — `F3-030`.

        Mevcut görünürlükler saklanır; `clear_solo()` bunları geri yükler.
        Zaten bu kanal solo ise bir şey yapmaz. Bilinmeyen kanal `KeyError`.
        """
        if channel_id not in self._series:
            raise KeyError(f"Grafikte yok: {channel_id}")
        if self._solo_id == channel_id:
            return
        if self._pre_solo_visibility is None:
            self._pre_solo_visibility = {
                cid: bool(curve.isVisible()) for cid, (_c, curve) in self._series.items()
            }
        self._solo_id = channel_id
        for cid, (_c, curve) in self._series.items():
            curve.setVisible(cid == channel_id)

    def clear_solo(self) -> None:
        """Solo'yu kapatır ve solo öncesi görünürlükleri geri yükler — `F3-030`."""
        if self._solo_id is None:
            return
        snapshot = self._pre_solo_visibility or {}
        for cid, (_c, curve) in self._series.items():
            curve.setVisible(snapshot.get(cid, True))
        self._solo_id = None
        self._pre_solo_visibility = None

    def toggle_solo(self, channel_id: str) -> None:
        """`channel_id` zaten solo ise solo'yu kapatır, değilse onu solo yapar."""
        if self._solo_id == channel_id:
            self.clear_solo()
        else:
            self.solo_series(channel_id)

    # -- seri bicimi: renk / cizgi / marker (F3-031) ------------

    @staticmethod
    def default_series_color(channel_id: str) -> str:
        """Kanalın **kalıcı** varsayılan rengi — panelden bağımsız — `F3-031`.

        Kabul kriteri: aynı kanal her panelde bu renkle açılır.
        """
        return channel_color(channel_id)

    def series_style(self, channel_id: str) -> SeriesStyle:
        """Serinin etkin çizim biçimi — `F3-031`. Bilinmeyen kanal `KeyError`."""
        if channel_id not in self._styles:
            raise KeyError(f"Grafikte yok: {channel_id}")
        return self._styles[channel_id]

    def series_color(self, channel_id: str) -> str:
        """Serinin etkin rengi (`#rrggbb`) — kısayol."""
        return self.series_style(channel_id).color

    _UNSET = object()

    def set_series_style(
        self,
        channel_id: str,
        *,
        color: str | None = None,
        width: int | None = None,
        line_style: str | None = None,
        symbol: object = _UNSET,
    ) -> None:
        """Bir serinin rengini/çizgisini/marker'ını değiştirir — `F3-031`.

        Yalnız verilen alanlar güncellenir. `symbol` açıkça `None`
        verilerek marker kaldırılabilir (bu yüzden ayrı sentinel).
        Geçersiz `line_style`/`symbol` `ValueError`, bilinmeyen kanal
        `KeyError`.
        """
        current = self.series_style(channel_id)
        if line_style is not None and line_style not in LINE_STYLES:
            raise ValueError(f"Bilinmeyen cizgi bicimi: {line_style!r}")
        new_symbol = current.symbol if symbol is self._UNSET else symbol
        if new_symbol is not None and new_symbol not in SERIES_SYMBOLS:
            raise ValueError(f"Bilinmeyen marker: {new_symbol!r}")

        self._styles[channel_id] = SeriesStyle(
            color=color if color is not None else current.color,
            width=width if width is not None else current.width,
            line_style=line_style if line_style is not None else current.line_style,
            symbol=new_symbol if new_symbol is None else str(new_symbol),
        )
        self._apply_style(channel_id)

    def _apply_style(self, channel_id: str) -> None:
        entry = self._series.get(channel_id)
        style = self._styles.get(channel_id)
        if entry is None or style is None:
            return
        curve = entry[1]
        curve.setPen(pg.mkPen(style.color, width=style.width, style=LINE_STYLES[style.line_style]))
        curve.setSymbol(style.symbol)
        if style.symbol is not None:
            curve.setSymbolBrush(style.color)
            curve.setSymbolPen(style.color)
            curve.setSymbolSize(6)

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
