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

from collections.abc import Sequence

from PySide6.QtWidgets import (
    QDockWidget,
    QGroupBox,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.event import Event
from sonar_analyzer.ui.cards.analysis_tools import AnalysisToolsCard
from sonar_analyzer.ui.cards.bit_status import BitStatusCard
from sonar_analyzer.ui.cards.data_export import DataExportCard
from sonar_analyzer.ui.cards.live_status import LiveStatusCard
from sonar_analyzer.ui.cards.recording_status import RecordingStatusCard
from sonar_analyzer.ui.docks.inspector import InspectorPanel

DOCK_OBJECT_NAME = "dock_right_column"
DOCK_TITLE = "BIT / Analysis / Export"

OVERVIEW_TAB_TITLE = "Overview"
INSPECTOR_TAB_TITLE = "Inspector"
#: `F5-020` canlı akış sağlığı. Ayrı sekmededir: mockup'ın dokuz bölgesi ve
#: Overview kart sırası (bölge 4/5/9) böylece hiç değişmez.
LIVE_TAB_TITLE = "Live"

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
        self.bit_status = BitStatusCard()
        self.analysis_tools = AnalysisToolsCard()
        self.data_export = DataExportCard()
        self.inspector = InspectorPanel()
        #: `F5-020` canlı akış sağlığı; kendi sekmesinde durur.
        self.live_status = LiveStatusCard()
        #: `F5-032` kayıt durumu; canlı sekmesinde sağlığın üstünde durur.
        self.recording_status = RecordingStatusCard()
        self.live_page = self._build_live_page()

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
            if name == "card_bit_status":
                # Gercek kart; yer tutucu yerine kullanilir (F1-035).
                self.bit_status.setParent(page)
                self.cards[name] = self.bit_status
                layout.addWidget(self.bit_status)
                continue
            if name == "card_analysis_tools":
                # Gercek kart; yer tutucu yerine kullanilir (F1-036).
                self.analysis_tools.setParent(page)
                self.cards[name] = self.analysis_tools
                layout.addWidget(self.analysis_tools)
                continue
            if name == "card_data_export":
                # Gercek kart; yer tutucu yerine kullanilir (F1-037).
                self.data_export.setParent(page)
                self.cards[name] = self.data_export
                layout.addWidget(self.data_export)
                continue

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

    def _build_live_page(self) -> QWidget:
        """`Live` sekmesinin içeriği: kayıt durumu + akış sağlığı — `F5-032`.

        İkisi aynı sekmede durur çünkü aynı soruyu tamamlar: veri geliyor
        mu (sağlık) ve diske yazılıyor mu (kayıt).

        Sayfa **ebeveynsiz** kurulur ve ebeveynini ancak sekme açılınca
        (`open_live_tab`) alır. `QDockWidget`'a bağlanıp düzenine hiç
        girmeyen bir alt widget, dock'un kendi düzeniyle çakışıp Qt
        tarafında çökmeye yol açıyordu; sekme açılana kadar sahipsiz
        durması `F5-020`'deki kart ile aynı, denenmiş ömür döngüsüdür.
        """
        page = QWidget()
        page.setObjectName("page_right_live")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        self.recording_status.setParent(page)
        layout.addWidget(self.recording_status)
        self.live_status.setParent(page)
        layout.addWidget(self.live_status)
        layout.addStretch(1)
        return page

    # -- bagalamsal sekme ------------------------------------------------

    @property
    def inspector_is_open(self) -> bool:
        return self.tabs.indexOf(self.inspector) >= 0

    def show_channel(self, channel: ChannelMetadata) -> None:
        """Inspector sekmesini açar (yoksa ekler) ve kanalı gösterir."""
        self.inspector.show_channel(channel)
        self._open_inspector_tab()

    def show_event(self, event: Event, related: Sequence[ChannelMetadata]) -> None:
        """Inspector sekmesini açar ve seçili olayın ayrıntısını gösterir — `F3-044`."""
        self.inspector.show_event(event, related)
        self._open_inspector_tab()

    def _open_inspector_tab(self) -> None:
        index = self.tabs.indexOf(self.inspector)
        if index < 0:
            index = self.tabs.addTab(self.inspector, INSPECTOR_TAB_TITLE)
        self.tabs.setCurrentIndex(index)

    # -- canli sekmesi (F5-020) ------------------------------------------

    @property
    def live_tab_is_open(self) -> bool:
        return self.tabs.indexOf(self.live_page) >= 0

    def open_live_tab(self) -> None:
        """`Live` sekmesini ekler (zaten varsa etkisiz).

        Inspector'la **aynı** desen: sekme varsayılan düzende yoktur, bir
        canlı kaynak takılınca belirir. Böylece mockup'ın açılış görünümü
        (`docs/ui/layout-map.md`) hiç değişmez.
        """
        if not self.live_tab_is_open:
            self.live_page.setParent(self.tabs)
            self.tabs.addTab(self.live_page, LIVE_TAB_TITLE)

    def close_live_tab(self) -> None:
        """`Live` sekmesini kaldırır ve sayaçları temizler."""
        index = self.tabs.indexOf(self.live_page)
        if index >= 0:
            self.tabs.removeTab(index)
            # Sekme kaldirilinca Qt widget'in ebeveynini birakiyor; nesne
            # korunsun diye yeniden sahiplenilir (close_inspector ile ayni).
            self.live_page.setParent(self)
            self.live_status.clear()
            self.recording_status.clear()

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
