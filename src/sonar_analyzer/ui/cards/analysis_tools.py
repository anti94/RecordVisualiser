"""Analysis Tools kartı — `F1-036`.

Mockup bölge 5 (`docs/ui/layout-map.md` §4): `Filter` / `FFT` / `Statistics` /
`Custom` sekmeleri, parametre alanları ve `Apply Filter`.

Bu iş yalnız **yerleşimdir**. Hiçbir hesaplama motoru henüz yok (Faz 4);
bu yüzden uygulama eylemleri pasif ve nedeni ipucunda yazıyor
(`ui/actions.py` `NOT_YET_AVAILABLE`, plan Bölüm 3.1). İşlevi olmayan alanda
gerçek sonuç izlenimi veren sahte çıktı gösterilmez.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE

CARD_OBJECT_NAME = "card_analysis_tools"
CARD_TITLE = "Analysis Tools"

#: Mockup sirasi.
TAB_TITLES: tuple[str, ...] = ("Filter", "FFT", "Statistics", "Custom")

FILTER_TYPES: tuple[str, ...] = ("Butterworth", "Chebyshev", "Bessel")


def _placeholder_tab(parent: QWidget, name: str) -> QWidget:
    """Henüz hesaplama motoru olmayan sekmenin gövdesi."""
    page = QWidget(parent)
    layout = QVBoxLayout(page)
    note = QLabel(f"{name} — {NOT_YET_AVAILABLE}.", page)
    note.setObjectName(f"label_{name.lower()}_placeholder")
    note.setWordWrap(True)
    note.setMinimumWidth(1)
    layout.addWidget(note)
    layout.addStretch(1)
    return page


class AnalysisToolsCard(QGroupBox):
    """Sağ sütunun orta kartı: Filter / FFT / Statistics / Custom."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(CARD_TITLE, parent)
        self.setObjectName(CARD_OBJECT_NAME)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("tabs_analysis_tools")
        self.tabs.addTab(self._build_filter_tab(), "Filter")
        self.tabs.addTab(_placeholder_tab(self, "FFT"), "FFT")
        self.tabs.addTab(_placeholder_tab(self, "Statistics"), "Statistics")
        self.tabs.addTab(_placeholder_tab(self, "Custom"), "Custom")
        layout.addWidget(self.tabs)

    def _build_filter_tab(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)

        self.filter_type = QComboBox(page)
        self.filter_type.setObjectName("combo_filter_type")
        self.filter_type.addItems(FILTER_TYPES)
        form.addRow("Filter Type", self.filter_type)

        self.cutoff_frequency = QSpinBox(page)
        self.cutoff_frequency.setObjectName("spin_cutoff_frequency")
        self.cutoff_frequency.setRange(1, 1_000_000)
        self.cutoff_frequency.setValue(100)
        self.cutoff_frequency.setSuffix(" Hz")
        form.addRow("Cutoff Frequency (Hz)", self.cutoff_frequency)

        self.order = QSpinBox(page)
        self.order.setObjectName("spin_filter_order")
        self.order.setRange(1, 16)
        self.order.setValue(4)
        form.addRow("Order", self.order)

        self.apply_to_selected = QCheckBox("Apply to selected channel", page)
        self.apply_to_selected.setObjectName("check_apply_to_selected")
        self.apply_to_selected.setChecked(True)
        form.addRow(self.apply_to_selected)

        self.show_filtered_data = QCheckBox("Show filtered data", page)
        self.show_filtered_data.setObjectName("check_show_filtered_data")
        form.addRow(self.show_filtered_data)

        self.apply_filter_button = QPushButton("Apply Filter", page)
        self.apply_filter_button.setObjectName("button_apply_filter")
        self.apply_filter_button.setEnabled(False)
        self.apply_filter_button.setToolTip(NOT_YET_AVAILABLE)
        form.addRow(self.apply_filter_button)

        return page

    # -- sorgular ----------------------------------------------------------

    def tab_titles(self) -> list[str]:
        return [self.tabs.tabText(index) for index in range(self.tabs.count())]
