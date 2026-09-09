"""Sağ sütun: kartlar ve bağlamsal Inspector sekmesi — `F1-025`.

Mockup bölge 4, 5 ve 9 (`docs/ui/layout-map.md` §4) alt alta üç karttır:
`BIT / System Status`, `Analysis Tools`, `Data Export`.

Plan Bölüm 5.1: *"Inspector, kanal veya olay seçimiyle açılan bağlamsal araç
sekmesidir; sağ sütundaki kartların yerini **kalıcı olarak almaz**."*

Bu yüzden sağ sütun bir sekme kabıdır:

* Sekme 0 — `Overview`: üç kart. Her zaman vardır ve **hiç kaldırılmaz**.
* Sekme 1 — `Inspector`: yalnız bir seçim yapılınca eklenir, kapatılınca
  kaldırılır. Kartlar bu sırada yerinde durur; sekme geri dönüldüğünde
  yeniden kurulmaz.

Qt'nin "tabified dock" yapısı yerine gerçek bir `QTabWidget` kullanılır: orada
aynı anda yalnız bir dock görünür sayıldığı için "kartlar duruyor mu" sorusu
güvenilir biçimde yanıtlanamıyordu.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDockWidget,
    QGroupBox,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.ui.docks.inspector import InspectorPanel

DOCK_OBJECT_NAME = "dock_right_column"
DOCK_TITLE = "BIT / Analysis / Export"

OVERVIEW_TAB_TITLE = "Overview"
INSPECTOR_TAB_TITLE = "Inspector"

#: (kart adi, baslik, aciklama) — mockup sirasiyla.
CARD_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "card_bit_status",
        "BIT / System Status",
        "Genel durum, Run BIT Analysis ve alt sistem tablosu (bolge 4).",
    ),
    (
        "card_analysis_tools",
        "Analysis Tools",
        "Filter / FFT / Statistics / Custom sekmeleri (bolge 5).",
    ),
    (
        "card_data_export",
        "Data Export",
        "Export Format, secili aralik ve metadata secenekleri (bolge 9).",
    ),
)


class RightColumnDock(QDockWidget):
    """Sağ sütun paneli: kartlar + bağlamsal Inspector."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(DOCK_TITLE, parent)
        self.setObjectName(DOCK_OBJECT_NAME)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        self.cards: dict[str, QGroupBox] = {}
        self.inspector = InspectorPanel()

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("tabs_right_column")
        self.tabs.setTabsClosable(False)
        self.tabs.addTab(self._build_overview(), OVERVIEW_TAB_TITLE)
        self.setWidget(self.tabs)

    # -- kurulum ---------------------------------------------------------

    def _build_overview(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("page_right_overview")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        for name, title, detail in CARD_SPECS:
            card = QGroupBox(title, page)
            card.setObjectName(name)

            card_layout = QVBoxLayout(card)
            note = QLabel(detail, card)
            note.setWordWrap(True)
            note.setMinimumWidth(1)
            card_layout.addWidget(note)

            self.cards[name] = card
            layout.addWidget(card)

        layout.addStretch(1)
        return page

    # -- bagalamsal sekme ------------------------------------------------

    @property
    def inspector_is_open(self) -> bool:
        return self.tabs.indexOf(self.inspector) >= 0

    def show_channel(self, channel: ChannelMetadata) -> None:
        """Inspector sekmesini açar (yoksa ekler) ve kanalı gösterir."""
        self.inspector.show_channel(channel)
        index = self.tabs.indexOf(self.inspector)
        if index < 0:
            index = self.tabs.addTab(self.inspector, INSPECTOR_TAB_TITLE)
        self.tabs.setCurrentIndex(index)

    def close_inspector(self) -> None:
        """Inspector sekmesini kaldırır; kartlar yerinde kalır."""
        index = self.tabs.indexOf(self.inspector)
        if index >= 0:
            self.tabs.removeTab(index)
            # Sekme kaldirilinca Qt widget'in ebeveynini birakiyor; panel
            # nesnesi korunsun diye yeniden sahiplenilir.
            self.inspector.setParent(self)
            self.inspector.clear()
        self.tabs.setCurrentIndex(0)

    # -- sorgular --------------------------------------------------------

    def tab_titles(self) -> list[str]:
        return [self.tabs.tabText(index) for index in range(self.tabs.count())]

    def card_titles(self) -> list[str]:
        """Kart başlıkları, görünen sırayla."""
        return [self.cards[name].title() for name, _, _ in CARD_SPECS]
