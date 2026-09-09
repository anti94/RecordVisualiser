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

from PySide6.QtWidgets import QLabel, QProgressBar, QStatusBar, QWidget

EMPTY_VALUE = "—"
READY_TEXT = "Ready"

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


class AppStatusBar(QStatusBar):
    """Mockup alt şeridi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("status_bar")

        self._fields: dict[str, QLabel] = {}
        for name, default in FIELD_SPECS:
            label = QLabel(default, self)
            label.setObjectName(f"status_{name}")
            self._fields[name] = label
            self.addWidget(label)

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

    def set_cursor_time(self, seconds: float | None) -> None:
        """İmlecin bulunduğu an; `None` ise alan boşalır."""
        self.set_field("cursor", EMPTY_VALUE if seconds is None else f"t = {seconds:.3f} s")

    def update_memory(self, usage: MemoryUsage | None = None) -> None:
        """Bellek göstergesini tazeler."""
        measured = usage if usage is not None else read_memory_usage()
        if measured is None:
            self.memory_label.setText(EMPTY_VALUE)
            self.memory_bar.setValue(0)
            return
        self.memory_label.setText(str(measured))
        self.memory_bar.setValue(round(measured.ratio * 100))
