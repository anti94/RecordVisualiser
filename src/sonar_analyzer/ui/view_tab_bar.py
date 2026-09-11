"""Mockup ana analiz sekmeleri — `F1-038`.

Mockup bölge 6 (`docs/ui/layout-map.md` §2, §3): merkezin en üstünde sekiz
sekme — `Time Series`, `Spectrum`, `Spectrogram`, `Cross Analysis`,
`BIT / Status`, `Transmission`, `3D View`, `Report`.

Bu iş **yerleşim + etkin sekmelerdir**. `F3-048` ile `Transmission` de
çalışır; kalan sekmeler plan Bölüm 22.4'e göre henüz desteklenmiyor ve
**açıkça pasif** gösteriliyor — gizlenmiyor, tıklanamıyor, nedeni
ipucunda yazıyor:

* `Spectrum`, `Spectrogram` → Faz 4 (`F4-045` ve civarı).
* `Transmission` → **çalışıyor** (`F3-048`).
* `BIT / Status` → Faz 3.
* `Cross Analysis`, `3D View`, `Report` → opsiyonel backlog (plan Bölüm 22.4).
"""

from __future__ import annotations

from PySide6.QtWidgets import QTabBar, QWidget

from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE

#: Mockup sirasi (docs/ui/layout-map.md §3).
TAB_TITLES: tuple[str, ...] = (
    "Time Series",
    "Spectrum",
    "Spectrogram",
    "Cross Analysis",
    "BIT / Status",
    "Transmission",
    "3D View",
    "Report",
)

#: Bu fazda calisan sekmeler (`F3-048` `Transmission`, `F4-045` `Spectrum`,
#: `F4-051` `Spectrogram` = waterfall gorunumu, `F4-081` `BIT / Status`).
ENABLED_TABS: frozenset[str] = frozenset(
    {"Time Series", "Transmission", "Spectrum", "Spectrogram", "BIT / Status"}
)


class ViewTabBar(QTabBar):
    """Merkezin en üstündeki sekiz sekmeli çubuk."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("view_tab_bar")

        for title in TAB_TITLES:
            index = self.addTab(title)
            enabled = title in ENABLED_TABS
            self.setTabEnabled(index, enabled)
            if not enabled:
                self.setTabToolTip(index, NOT_YET_AVAILABLE)

        self.setCurrentIndex(self.tab_titles().index("Time Series"))

    def tab_titles(self) -> list[str]:
        return [self.tabText(index) for index in range(self.count())]

    def enabled_tabs(self) -> list[str]:
        return [self.tabText(index) for index in range(self.count()) if self.isTabEnabled(index)]
