"""Data Export kartı — `F1-037`.

Mockup bölge 9 (`docs/ui/layout-map.md` §4): `Export Format`,
`Export selected time range`, `Include metadata`, `Export Data`.

Bu iş yalnız **yerleşimdir**; dışa aktarma motoru sonraki fazda gelir
(plan Bölüm 15). `Export Data` bu yüzden pasif ve nedeni ipucunda yazıyor
(`ui/actions.py` `NOT_YET_AVAILABLE`).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QWidget,
)

from sonar_analyzer.ui.actions import NOT_YET_AVAILABLE

CARD_OBJECT_NAME = "card_data_export"
CARD_TITLE = "Data Export"

#: Plan Bolum 15.1: desteklenecek ciktilar.
EXPORT_FORMATS: tuple[str, ...] = ("CSV", "TSV", "JSON", "PNG", "SVG")


class DataExportCard(QGroupBox):
    """Sağ sütunun alt kartı."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(CARD_TITLE, parent)
        self.setObjectName(CARD_OBJECT_NAME)

        form = QFormLayout(self)
        form.setContentsMargins(6, 6, 6, 6)

        self.export_format = QComboBox(self)
        self.export_format.setObjectName("combo_export_format")
        self.export_format.addItems(EXPORT_FORMATS)
        form.addRow("Export Format", self.export_format)

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
        self.export_button.setEnabled(False)
        self.export_button.setToolTip(NOT_YET_AVAILABLE)
        form.addRow(self.export_button)
