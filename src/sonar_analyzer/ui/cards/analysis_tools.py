"""Analysis Tools kartı — `F1-036`.

Mockup bölge 5 (`docs/ui/layout-map.md` §4): `Filter` / `FFT` / `Statistics` /
`Custom` sekmeleri, parametre alanları ve `Apply Filter`.

Bu iş yalnız **yerleşimdir**. Hiçbir hesaplama motoru henüz yok (Faz 4);
bu yüzden uygulama eylemleri pasif ve nedeni ipucunda yazıyor
(`ui/actions.py` `NOT_YET_AVAILABLE`, plan Bölüm 3.1). İşlevi olmayan alanda
gerçek sonuç izlenimi veren sahte çıktı gösterilmez.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
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

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE
from sonar_analyzer.ui.cards.step_list_editor import StepListEditor

CARD_OBJECT_NAME = "card_analysis_tools"
CARD_TITLE = "Analysis Tools"

#: Mockup sirasi.
TAB_TITLES: tuple[str, ...] = ("Filter", "FFT", "Statistics", "Custom")

#: Yaklaşım ailesi (mockup). Şu an yalnız Butterworth uygulanır.
FILTER_TYPES: tuple[str, ...] = ("Butterworth", "Chebyshev", "Bessel")

#: Filtre yanıt türü. `F4-029` low-pass ile başlar; `F4-032`/`F4-035`/
#: `F4-038` sırayla high-pass / band-pass / notch ekler.
FILTER_RESPONSES: tuple[str, ...] = ("Low-pass", "High-pass")

#: `filter_response` etiketi -> `StepKind` eşlemesi.
FILTER_RESPONSE_KINDS: dict[str, StepKind] = {
    "Low-pass": StepKind.LOW_PASS,
    "High-pass": StepKind.HIGH_PASS,
}


class FilterTabError(ValueError):
    """Filter sekmesi alanlarından geçerli bir işlem zinciri kurulamadı."""


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

    #: `F4-008` — `Apply Filter`'a basıldı; Custom sekmesindeki zincir uygulanır.
    apply_requested = Signal()
    #: `F4-008` — `Show filtered data` değişti (işlenmiş overlay görünürlüğü).
    show_filtered_toggled = Signal(bool)

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
        # F4-006: "Custom" sekmesi artık gerçek işlem listesi editörünü barındırır.
        self.step_editor = StepListEditor(self)
        self.tabs.addTab(self.step_editor, "Custom")
        layout.addWidget(self.tabs)

    def _build_filter_tab(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)

        self.filter_type = QComboBox(page)
        self.filter_type.setObjectName("combo_filter_type")
        self.filter_type.addItems(FILTER_TYPES)
        form.addRow("Filter Type", self.filter_type)

        self.filter_response = QComboBox(page)
        self.filter_response.setObjectName("combo_filter_response")
        self.filter_response.addItems(FILTER_RESPONSES)
        form.addRow("Response", self.filter_response)

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
        self.show_filtered_data.toggled.connect(self.show_filtered_toggled)
        form.addRow(self.show_filtered_data)

        # F4-008: buton artık Custom sekmesindeki işlem zincirini seçili
        # kanala uygular (gerçek IIR filtre adımları `F4-015`+ ile gelir).
        self.apply_filter_button = QPushButton("Apply Filter", page)
        self.apply_filter_button.setObjectName("button_apply_filter")
        self.apply_filter_button.setToolTip(
            "Custom sekmesindeki işlem zincirini seçili kanala uygula"
        )
        self.apply_filter_button.clicked.connect(self.apply_requested)
        form.addRow(self.apply_filter_button)

        return page

    # -- sorgular ----------------------------------------------------------

    def tab_titles(self) -> list[str]:
        return [self.tabs.tabText(index) for index in range(self.tabs.count())]

    def active_tab_title(self) -> str:
        return self.tabs.tabText(self.tabs.currentIndex())

    def build_filter_chain(self, channel_id: str, sample_rate_hz: float) -> ProcessingChain:
        """Filter sekmesi alanlarından tek adımlı bir `ProcessingChain` kurar — `F4-029`.

        Geçersiz parametre (Nyquist dışı cutoff, aralık dışı order,
        desteklenmeyen aile) `FilterTabError` yükseltir — çağıran bunu
        kullanıcıya gösterir, işlem başlatmaz.
        """
        family = self.filter_type.currentText()
        if family != "Butterworth":
            raise FilterTabError(f"{family} ailesi henüz uygulanmadı; Butterworth seçin.")
        if sample_rate_hz <= 0:
            raise FilterTabError("Kanal sample rate bilinmiyor; filtre uygulanamaz.")

        response = self.filter_response.currentText()
        kind = FILTER_RESPONSE_KINDS.get(response)
        if kind is None:  # pragma: no cover - combo yalnız bilinen değerleri taşır
            raise FilterTabError(f"Bilinmeyen yanıt türü: {response}")

        try:
            step = ProcessingStep(
                kind=kind,
                input_channel_id=channel_id,
                parameters={
                    "sample_rate_hz": float(sample_rate_hz),
                    "cutoff_hz": float(self.cutoff_frequency.value()),
                    "order": int(self.order.value()),
                },
            )
        except ValueError as exc:  # StepValidationError dahil
            raise FilterTabError(str(exc)) from exc
        return ProcessingChain([step])
