"""Data Export kartı — `F1-037`, `F3-065`.

Mockup bölge 9 (`docs/ui/layout-map.md` §4): `Export Format`,
`Export selected time range`, `Include metadata`, `Export Data`.

`F3-065`: kart artık gerçek dışa aktarmayı sürüyor. `Export Data`
etkin ve tıklanınca `export_requested` yayar; ayrıca **ham / işlenmiş**
veri seçimi açık bir alan olarak eklendi (CSV için anlamlı).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QWidget,
)

from sonar_analyzer.application.export_controller import DataVariant

CARD_OBJECT_NAME = "card_data_export"
CARD_TITLE = "Data Export"

#: Plan Bolum 15.1: desteklenecek ciktilar.
EXPORT_FORMATS: tuple[str, ...] = ("CSV", "TSV", "JSON", "PNG", "SVG")

#: (etiket, DataVariant) — ham/işlenmiş seçimi.
DATA_VARIANTS: tuple[tuple[str, DataVariant], ...] = (
    ("Processed (scaled)", DataVariant.PROCESSED),
    ("Raw (uncalibrated)", DataVariant.RAW),
)


class DataExportCard(QGroupBox):
    """Sağ sütunun alt kartı."""

    #: Kullanıcı `Export Data`'ya bastı — `F3-065`.
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(CARD_TITLE, parent)
        self.setObjectName(CARD_OBJECT_NAME)

        form = QFormLayout(self)
        form.setContentsMargins(6, 6, 6, 6)

        self.export_format = QComboBox(self)
        self.export_format.setObjectName("combo_export_format")
        self.export_format.addItems(EXPORT_FORMATS)
        form.addRow("Export Format", self.export_format)

        # F3-065: ham / işlenmiş veri seçimi açık bir alan.
        self.data_variant = QComboBox(self)
        self.data_variant.setObjectName("combo_data_variant")
        for label, variant in DATA_VARIANTS:
            self.data_variant.addItem(label, variant)
        self.data_variant.setToolTip(
            "Processed: repository'den gelen ölçekli değerler.\n"
            "Raw: kalibrasyon geri alınmış ham değerler (CSV)."
        )
        form.addRow("Data", self.data_variant)

        self.export_selected_range = QCheckBox("Export selected time range", self)
        self.export_selected_range.setObjectName("check_export_selected_range")
        self.export_selected_range.setChecked(True)
        form.addRow(self.export_selected_range)

        self.include_metadata = QCheckBox("Include metadata", self)
        self.include_metadata.setObjectName("check_include_metadata")
        self.include_metadata.setChecked(True)
        form.addRow(self.include_metadata)

        self.export_button = QPushButton("Export Data", self)
        self.export_button.setObjectName("button_export_data")
        self.export_button.clicked.connect(self.export_requested)
        form.addRow(self.export_button)

    # -- durum okuyucular ---------------------------------------------

    def selected_format(self) -> str:
        return self.export_format.currentText()

    def selected_variant(self) -> DataVariant:
        # Qt, str tabanlı enum'u düz `str` olarak geri verebilir; değere göre çöz.
        data = self.data_variant.currentData()
        try:
            return DataVariant(data)
        except ValueError:
            return DataVariant.PROCESSED

    def wants_selected_range(self) -> bool:
        return self.export_selected_range.isChecked()

    def wants_metadata(self) -> bool:
        return self.include_metadata.isChecked()
