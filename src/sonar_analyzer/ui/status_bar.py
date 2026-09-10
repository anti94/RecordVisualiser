"""Durum çubuğu alanları — `F1-028`.

Mockup alt şeridi (`docs/ui/layout-map.md` §6): solda işlem durumu, sağda bellek
göstergesi. Plan Bölüm 5.1 ayrıca dosya, bağlantı ve cursor alanlarını ister.

Alanlar sabit sıradadır ve **hiçbiri gizlenmez**; değeri yoksa `—` gösterilir.
Böylece kullanıcı bir alanın boş mu yoksa yok mu olduğunu ayırt eder.

Bellek ölçümü ek bağımlılık gerektirmez: Windows'ta PSAPI/`GlobalMemoryStatusEx`
`ctypes` ile çağrılır. Ölçüm alınamazsa gösterge `—` olur ve uygulama etkilenmez.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QWidget,
)

from sonar_analyzer.application.time_display import (
    MODE_LABEL,
    TimeDisplayMode,
    format_instant,
    next_mode,
)

EMPTY_VALUE = "—"
READY_TEXT = "Ready"
LOADING_TEXT = "Loading..."
CANCELLED_TEXT = "Yukleme iptal edildi"

#: (alan adi, ontanimli metin) — soldan saga.
FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("status", READY_TEXT),
    ("file", EMPTY_VALUE),
    ("connection", EMPTY_VALUE),
    ("cursor", EMPTY_VALUE),
)

BYTES_PER_GB = 1024**3


@dataclass(frozen=True)
class MemoryUsage:
    """Süreç kullanımı ve toplam fiziksel bellek (bayt)."""

    used_bytes: int
    total_bytes: int

    @property
    def ratio(self) -> float:
        return 0.0 if self.total_bytes <= 0 else self.used_bytes / self.total_bytes

    def __str__(self) -> str:
        used = self.used_bytes / BYTES_PER_GB
        total = self.total_bytes / BYTES_PER_GB
        return f"Memory: {used:.1f} / {total:.1f} GB"


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = (
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    )


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = (
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    )


def read_memory_usage() -> MemoryUsage | None:
    """Süreç ve sistem belleğini okur; okunamazsa `None`."""
    if sys.platform != "win32":  # pragma: no cover - hedef platform Windows
        return None

    try:
        kernel32 = ctypes.WinDLL("kernel32")  # type: ignore[attr-defined]
        psapi = ctypes.WinDLL("psapi")  # type: ignore[attr-defined]

        # restype/argtypes BILEREK verilir: GetCurrentProcess sozde tanitici
        # olarak -1 dondurur ve varsayilan c_int donusuyle 64-bit HANDLE'a
        # gecerken bozulur; cagri sessizce basarisiz olur.
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
        kernel32.GlobalMemoryStatusEx.restype = ctypes.c_int
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int

        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None

        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
        handle = kernel32.GetCurrentProcess()
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), ctypes.sizeof(counters)):
            return None

        return MemoryUsage(int(counters.WorkingSetSize), int(status.ullTotalPhys))
    except (OSError, AttributeError, ValueError):
        # Olcum alinamazsa gosterge bos kalir; uygulama etkilenmez.
        return None


class ClickableLabel(QLabel):
    """Sol tıklamada sinyal yayan etiket (imleç zamanı kipini döndürmek için)."""

    clicked = Signal()

    def mousePressEvent(self, ev: QMouseEvent) -> None:  # Qt override
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            ev.accept()
            return
        super().mousePressEvent(ev)


class AppStatusBar(QStatusBar):
    """Mockup alt şeridi."""

    #: Kullanıcı yükleme iptalini istedi (`F3-003`).
    cancel_requested = Signal()
    #: `F3-061` imleç zamanı gösterim kipi değişti.
    cursor_time_mode_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("status_bar")

        self.cursor_time_label = ClickableLabel(EMPTY_VALUE, self)

        self._fields: dict[str, QLabel] = {}
        for name, default in FIELD_SPECS:
            label: QLabel = self.cursor_time_label if name == "cursor" else QLabel(default, self)
            label.setText(default)
            label.setObjectName(f"status_{name}")
            self._fields[name] = label
            self.addWidget(label)

        # F3-061: imleç anı üç görünüm arasında tıklamayla döner.
        self._cursor_mode = TimeDisplayMode.ELAPSED
        self._cursor_seconds: float | None = None
        self._time_origin_ns: int | None = None
        self.cursor_time_label.setToolTip("Tikla: UTC / yerel / gecen sure")
        self.cursor_time_label.clicked.connect(self.cycle_cursor_time_mode)

        self.memory_label = QLabel(EMPTY_VALUE, self)
        self.memory_label.setObjectName("status_memory")
        self.addPermanentWidget(self.memory_label)

        self.memory_bar = QProgressBar(self)
        self.memory_bar.setObjectName("status_memory_bar")
        self.memory_bar.setRange(0, 100)
        self.memory_bar.setValue(0)
        self.memory_bar.setTextVisible(False)
        self.memory_bar.setFixedWidth(80)
        self.addPermanentWidget(self.memory_bar)

        # Yukleme ilerlemesi ve iptali (F3-003). Bosta gizlidir; yalniz bir
        # istek surerken gorunur, boylece alt serit normalde kalabalasmaz.
        self.load_bar = QProgressBar(self)
        self.load_bar.setObjectName("status_load_bar")
        self.load_bar.setRange(0, 100)
        self.load_bar.setValue(0)
        self.load_bar.setFixedWidth(120)
        self.load_bar.hide()
        self.addPermanentWidget(self.load_bar)

        self.cancel_button = QPushButton("Iptal", self)
        self.cancel_button.setObjectName("button_cancel_load")
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.addPermanentWidget(self.cancel_button)

    # -- alanlar ---------------------------------------------------------

    def field_names(self) -> list[str]:
        return [name for name, _ in FIELD_SPECS] + ["memory"]

    def field_value(self, name: str) -> str:
        """Alanın gösterilen değeri — testler ve kabul için."""
        if name == "memory":
            return self.memory_label.text()
        try:
            return self._fields[name].text()
        except KeyError as exc:
            raise KeyError(f"Tanimsiz durum alani: {name}") from exc

    def set_field(self, name: str, value: str) -> None:
        try:
            label = self._fields[name]
        except KeyError as exc:
            raise KeyError(f"Tanimsiz durum alani: {name}") from exc
        label.setText(value or EMPTY_VALUE)

    def set_status(self, text: str) -> None:
        """Sol taraftaki işlem durumu (`Ready`, `Parsing…`, `Indexing…`)."""
        self.set_field("status", text or READY_TEXT)

    def set_time_origin(self, start_ns: int | None) -> None:
        """Kayıt başlangıcının kanonik anı — UTC/yerel görünümler bunu kullanır."""
        self._time_origin_ns = start_ns
        self._render_cursor()

    def set_cursor_time(self, seconds: float | None) -> None:
        """İmlecin kayıt başından bu yana geçen süresi; `None` ise alan boşalır."""
        self._cursor_seconds = seconds
        self._render_cursor()

    @property
    def cursor_time_mode(self) -> TimeDisplayMode:
        return self._cursor_mode

    def cycle_cursor_time_mode(self) -> TimeDisplayMode:
        """İmleç zamanı görünümünü döndürür (elapsed -> UTC -> local -> ...)."""
        self._cursor_mode = next_mode(self._cursor_mode)
        self._render_cursor()
        self.cursor_time_mode_changed.emit(self._cursor_mode)
        return self._cursor_mode

    def _render_cursor(self) -> None:
        """`cursor` alanını mevcut kip ve ana göre yeniden çizer — `F3-061`."""
        seconds = self._cursor_seconds
        if seconds is None:
            self.set_field("cursor", EMPTY_VALUE)
            return
        elapsed_ns = round(seconds * 1_000_000_000)
        mode = self._cursor_mode
        origin = self._time_origin_ns
        if mode is not TimeDisplayMode.ELAPSED and origin is None:
            # Mutlak an bilinmiyor: geçen süreye düş, ama kip seçimi korunur.
            self.set_field(
                "cursor",
                format_instant(elapsed_ns, TimeDisplayMode.ELAPSED, start_ns=0),
            )
            return
        timestamp_ns = elapsed_ns + (origin or 0)
        self.set_field(
            "cursor",
            format_instant(timestamp_ns, mode, start_ns=origin or 0),
        )

    def cursor_time_mode_label(self) -> str:
        """Mevcut kipin kısa adı — ipuçları / testler için."""
        return MODE_LABEL[self._cursor_mode]

    # -- yukleme ilerlemesi (F3-003) --------------------------------------

    def start_load_progress(self, total: int) -> None:
        """İlerleme çubuğunu ve iptal düğmesini görünür yapar."""
        self.load_bar.setRange(0, max(1, total))
        self.load_bar.setValue(0)
        self.load_bar.setFormat(f"0/{total}")
        self.load_bar.show()
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        self.set_status(LOADING_TEXT)

    def set_load_progress(self, completed: int, total: int) -> None:
        self.load_bar.setRange(0, max(1, total))
        self.load_bar.setValue(completed)
        self.load_bar.setFormat(f"{completed}/{total}")

    def finish_load_progress(self, status_text: str = READY_TEXT) -> None:
        """Yükleme bitti ya da iptal edildi: gösterge gizlenir."""
        self.load_bar.hide()
        self.cancel_button.hide()
        self.set_status(status_text)

    @property
    def load_in_progress(self) -> bool:
        return self.load_bar.isVisible()

    def update_memory(self, usage: MemoryUsage | None = None) -> None:
        """Bellek göstergesini tazeler."""
        measured = usage if usage is not None else read_memory_usage()
        if measured is None:
            self.memory_label.setText(EMPTY_VALUE)
            self.memory_bar.setValue(0)
            return
        self.memory_label.setText(str(measured))
        self.memory_bar.setValue(round(measured.ratio * 100))
