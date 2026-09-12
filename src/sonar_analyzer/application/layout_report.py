"""Paketli uygulamanın ana ekran raporu — `F6-031`.

Kabul: **Dokuz bölge, hiyerarşi, tema ve çalışan ana analizler kabul
listesini karşılar.**

`F6-005` paketin açıldığını, `F6-006` iş yaptığını gösterdi. Bu modül
**ne gösterdiğini** rapor eder: dokuz bölgenin hangi alanda olduğunu,
sütun genişliklerini, sekme çubuğunu, temanın uygulanıp
uygulanmadığını ve ana analiz panelinin gerçekten sonuç üretip
üretmediğini.

Rapor, çalışan pencereden **ölçülerek** çıkarılır; bir listeden
kopyalanmaz. Kaynak ağacındaki testler yerleşimi zaten denetliyor
(`F3-079`); buradaki değer, aynı şeyin **pakette de** doğru olduğunu
göstermesidir. Paketlemede kaybolan tema dosyası ya da gelmeyen bir
panel, yalnız burada görünür.

Ana analizin "çalıştığı" iddiası da ölçülür: gerçek bir kayıttan
okunan örnekler üretim spektrum paneline verilir ve panelin bir eğri
üretip üretmediğine bakılır. Sekmenin etkin görünmesi, arkasındaki
hesabın çalıştığını göstermez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - yalniz tip denetimi
    from sonar_analyzer.ui.main_window import MainWindow

#: `docs/ui/layout-map.md` §2 — dokuz bolge -> (nesne adi, beklenen alan).
#: Alan: "left" | "center" | "right" | "bottom".
NINE_REGIONS: tuple[tuple[int, str, str, str], ...] = (
    (1, "Dosya ve Veri Yönetimi", "dock_data_explorer", "left"),
    (2, "Hızlı Araçlar", "toolbar_quick_tools", "center"),
    (3, "Görselleştirme Alanı", "center_stack", "center"),
    (4, "Donanım/BIT Durumu", "card_bit_status", "right"),
    (5, "Hesaplamalar ve Analiz", "card_analysis_tools", "right"),
    (6, "Çoklu Görünüm", "view_tab_bar", "center"),
    (7, "Zaman Kontrolü", "dock_playback", "bottom"),
    (8, "Log / Mesajlar", "dock_bottom_panel", "bottom"),
    (9, "Ayarlar ve Dışa Aktarma", "card_data_export", "right"),
)


@dataclass
class LayoutReport:
    """Ana ekranın ölçülmüş hâli."""

    lines: list[str] = field(default_factory=lambda: [])
    failures: list[str] = field(default_factory=lambda: [])
    data: dict[str, Any] = field(default_factory=lambda: {})

    @property
    def ok(self) -> bool:
        return not self.failures


def _area_of(window: MainWindow, widget: Any) -> str:
    """Bir gereci içeren bölgeyi ana pencerenin kendi yerleşiminden okur."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDockWidget, QToolBar

    node: Any = widget
    while node is not None:
        if isinstance(node, QDockWidget):
            area = window.dockWidgetArea(node)
            return {
                Qt.DockWidgetArea.LeftDockWidgetArea: "left",
                Qt.DockWidgetArea.RightDockWidgetArea: "right",
                Qt.DockWidgetArea.BottomDockWidgetArea: "bottom",
                Qt.DockWidgetArea.TopDockWidgetArea: "top",
            }.get(area, "bilinmiyor")
        if isinstance(node, QToolBar):
            return "center"
        if node is window.centralWidget():
            return "center"
        node = node.parentWidget()
    return "bilinmiyor"


def _collect_regions(window: MainWindow) -> tuple[list[dict[str, Any]], list[str]]:
    """Dokuz bölgeyi pencerede arar ve alanlarını ölçer."""
    from PySide6.QtWidgets import QWidget

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for number, label, object_name, expected_area in NINE_REGIONS:
        widget = window.findChild(QWidget, object_name)
        if widget is None:
            failures.append(f"bolge {number} ({object_name}) bulunamadi")
            rows.append(
                {
                    "region": number,
                    "label": label,
                    "object_name": object_name,
                    "found": False,
                    "visible": False,
                    "expected_area": expected_area,
                    "actual_area": "yok",
                }
            )
            continue
        actual = _area_of(window, widget)
        visible = widget.isVisible()
        if actual != expected_area:
            failures.append(f"bolge {number}: alan {actual}, beklenen {expected_area}")
        if not visible:
            failures.append(f"bolge {number} gorunur degil")
        rows.append(
            {
                "region": number,
                "label": label,
                "object_name": object_name,
                "found": True,
                "visible": visible,
                "expected_area": expected_area,
                "actual_area": actual,
                "width": widget.width(),
                "height": widget.height(),
            }
        )
    return rows, failures


def _collect_tabs(window: MainWindow) -> tuple[dict[str, Any], list[str]]:
    """Sekme çubuğunu ve hangi görünümlerin etkin olduğunu ölçer."""
    from PySide6.QtWidgets import QTabBar

    from sonar_analyzer.ui.view_tab_bar import ENABLED_TABS, TAB_TITLES

    failures: list[str] = []
    bar = window.findChild(QTabBar, "view_tab_bar")
    if bar is None:
        return {"found": False}, ["sekme cubugu (tabs_view) bulunamadi"]

    titles = [bar.tabText(index) for index in range(bar.count())]
    enabled = [bar.tabText(i) for i in range(bar.count()) if bar.isTabEnabled(i)]
    current = bar.tabText(bar.currentIndex()) if bar.count() else ""
    if tuple(titles) != TAB_TITLES:
        failures.append(f"sekme sirasi farkli: {titles}")
    if set(enabled) != set(ENABLED_TABS):
        failures.append(f"etkin sekmeler farkli: {sorted(enabled)}")
    if current != "Time Series":
        failures.append(f"acilista secili sekme {current!r}, beklenen 'Time Series'")
    return {"found": True, "titles": titles, "enabled": enabled, "current": current}, failures


def _collect_columns(window: MainWindow) -> tuple[dict[str, Any], list[str]]:
    """Sol ve sağ sütun genişlikleri — `layout-map.md` §1: 200 px / 300 px.

    Sütunlar "sabit-esnek"tir; pencere boyutuna ve DPI'a göre bir miktar
    oynar. Bu yüzden tam eşitlik değil, **mockup oranını bozmayan** bir
    aralık aranır: sabit bir piksele bağlanmak, farklı DPI'da yanlış
    alarm üretirdi.
    """
    from PySide6.QtWidgets import QDockWidget

    failures: list[str] = []
    measured: dict[str, Any] = {}
    for name, expected, tolerance in (
        ("dock_data_explorer", 200, 120),
        ("dock_right_column", 300, 150),
    ):
        dock = window.findChild(QDockWidget, name)
        if dock is None:
            failures.append(f"sutun bulunamadi: {name}")
            continue
        width = dock.width()
        measured[name] = {"width": width, "expected": expected, "tolerance": tolerance}
        if abs(width - expected) > tolerance:
            failures.append(f"{name} genisligi {width}, beklenen ~{expected} (+-{tolerance})")
    return measured, failures


def _collect_theme(window: MainWindow) -> tuple[dict[str, Any], list[str]]:
    """Temanın gerçekten uygulandığını ölçer (paketten gelmiş olmalı)."""
    from PySide6.QtGui import QPalette

    failures: list[str] = []
    stylesheet = window.styleSheet() or ""
    application = window.window()
    if not stylesheet:
        from PySide6.QtWidgets import QApplication

        instance = QApplication.instance()
        if isinstance(instance, QApplication):
            stylesheet = instance.styleSheet() or ""

    background = application.palette().color(QPalette.ColorRole.Window)
    lightness = background.lightness()
    if len(stylesheet) < 200:
        failures.append(f"stil sayfasi yok ya da cok kisa ({len(stylesheet)} karakter)")
    if lightness > 127:
        failures.append(f"koyu tema degil (arka plan aydinligi {lightness})")
    return (
        {
            "stylesheet_chars": len(stylesheet),
            "background": background.name(),
            "background_lightness": lightness,
        },
        failures,
    )


def _collect_analysis(window: MainWindow, source: Path | None) -> tuple[dict[str, Any], list[str]]:
    """Ana analizin gerçekten sonuç ürettiğini ölçer.

    Sekmenin etkin görünmesi, arkasındaki hesabın çalıştığını
    göstermez. Bu yüzden gerçek bir kayıttan okunan örnekler üretim
    spektrum paneline verilir ve bir eğri üretilip üretilmediğine
    bakılır.
    """
    import numpy as np

    if source is None:
        return {"attempted": False, "reason": "kayit verilmedi"}, ["analiz icin kayit verilmedi"]

    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    failures: list[str] = []
    repository = FileRecordingRepository()
    try:
        repository.open(source)
    except Exception as exc:  # pragma: no cover - paket disinda beklenmez
        return {"attempted": True, "opened": False, "error": str(exc)}, [f"kayit acilamadi: {exc}"]

    metadata = repository.metadata()
    channels = list(repository.channels())
    if not channels:
        return {"attempted": True, "opened": True, "channels": 0}, ["kayitta kanal yok"]

    channel = channels[0]
    chunk = repository.query(channel.id, metadata.time_range)
    values = np.asarray(chunk.values, dtype=np.float64)

    window.spectrum_view.set_channel_data(channel, values)
    has_spectrum = window.spectrum_view.has_spectrum
    if not has_spectrum:
        failures.append(f"spektrum uretilmedi: {window.spectrum_view.message_text()}")
        points = 0
    else:
        frequencies, amplitudes = window.spectrum_view.curve_data()
        points = int(frequencies.size)
        if points == 0 or amplitudes.size != frequencies.size:
            failures.append("spektrum egrisi bos ya da eksik")

    return (
        {
            "attempted": True,
            "opened": True,
            "channels": len(channels),
            "samples": int(values.size),
            "has_spectrum": has_spectrum,
            "spectrum_points": points,
            "frequency_axis": window.spectrum_view.frequency_axis_label(),
            "amplitude_axis": window.spectrum_view.amplitude_axis_label(),
        },
        failures,
    )


def build_layout_report(window: MainWindow, source: Path | None = None) -> LayoutReport:
    """Gösterilmiş bir ana ekranı ölçer ve raporlar."""
    regions, region_failures = _collect_regions(window)
    columns, column_failures = _collect_columns(window)
    tabs, tab_failures = _collect_tabs(window)
    theme, theme_failures = _collect_theme(window)
    analysis, analysis_failures = _collect_analysis(window, source)

    failures = [
        *region_failures,
        *column_failures,
        *tab_failures,
        *theme_failures,
        *analysis_failures,
    ]
    found = sum(1 for row in regions if row["found"] and row["visible"])

    lines = [
        f"bolge: {found}/{len(NINE_REGIONS)} gorunur ve dogru alanda",
        f"pencere: {window.width()}x{window.height()}",
        f"sekme: {len(tabs.get('titles', []))} baslik, {len(tabs.get('enabled', []))} etkin",
        f"tema: {theme['stylesheet_chars']} karakter, arka plan {theme['background']}",
    ]
    if analysis.get("has_spectrum"):
        lines.append(f"analiz: spektrum {analysis['spectrum_points']} nokta")
    else:
        lines.append("analiz: spektrum URETILMEDI")
    for failure in failures:
        lines.append(f"eksik: {failure}")
    lines.append("sonuc: " + ("TAMAM" if not failures else f"EKSIK -> {len(failures)} madde"))

    return LayoutReport(
        lines=lines,
        failures=failures,
        data={
            "window": {"width": window.width(), "height": window.height()},
            "regions": regions,
            "columns": columns,
            "tabs": tabs,
            "theme": theme,
            "analysis": analysis,
        },
    )
