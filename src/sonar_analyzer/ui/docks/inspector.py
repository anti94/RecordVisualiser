"""Inspector paneli — bağlamsal araç sekmesi içeriği (`F1-025`).

Plan Bölüm 5.1: *"Inspector, kanal veya olay seçimiyle açılan bağlamsal araç
sekmesidir; sağ sütundaki BIT, Analysis Tools ve Data Export kartlarının yerini
**kalıcı olarak almaz**."*

Bu sınıf yalnız içeriktir; sekme olarak açılıp kapanması
`ui/docks/right_column.py` içindedir.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata

PANEL_OBJECT_NAME = "panel_inspector"

EMPTY_VALUE = "—"
EMPTY_HINT = "Ayrinti icin bir kanal veya olay secin."

#: Kanal secildiginde gosterilen alanlar.
CHANNEL_FIELDS = ("Channel", "Path", "Unit", "Sample rate", "Data type", "Source", "Time base")


class InspectorPanel(QWidget):
    """Seçili kanalın ayrıntısını gösteren bağlamsal panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(PANEL_OBJECT_NAME)

        self._fields: dict[str, QLabel] = {}
        self._build_body()
        self.clear()

    def _build_body(self) -> None:
        body = self
        layout = QVBoxLayout(body)
        layout.setContentsMargins(6, 6, 6, 6)

        self.hint = QLabel(EMPTY_HINT, body)
        self.hint.setObjectName("label_inspector_hint")
        self.hint.setWordWrap(True)
        self.hint.setMinimumWidth(1)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint)

        self.detail = QWidget(body)
        form = QFormLayout(self.detail)
        form.setContentsMargins(0, 0, 0, 0)
        for field in CHANNEL_FIELDS:
            value = QLabel(EMPTY_VALUE, self.detail)
            value.setObjectName(f"label_inspector_{field.lower().replace(' ', '_')}")
            value.setWordWrap(True)
            value.setMinimumWidth(1)
            self._fields[field] = value
            form.addRow(f"{field}:", value)
        layout.addWidget(self.detail)

        layout.addStretch(1)

    def clear(self) -> None:
        """Seçim yokken boş duruma döner."""
        for label in self._fields.values():
            label.setText(EMPTY_VALUE)
        self.detail.setVisible(False)
        self.hint.setVisible(True)

    def show_channel(self, channel: ChannelMetadata) -> None:
        """Seçilen kanalın ayrıntısını gösterir."""
        rate = (
            f"{channel.sample_rate_hz:g} Hz" if channel.sample_rate_hz is not None else EMPTY_VALUE
        )
        values = {
            "Channel": channel.name,
            "Path": channel.path,
            "Unit": channel.unit or EMPTY_VALUE,
            "Sample rate": rate,
            "Data type": channel.dtype,
            "Source": channel.source.value,
            "Time base": channel.time_base_id,
        }
        for field, text in values.items():
            self._fields[field].setText(text)

        self.hint.setVisible(False)
        self.detail.setVisible(True)

    def field_value(self, field: str) -> str:
        """Alanın gösterilen değeri — testler ve kabul için."""
        try:
            return self._fields[field].text()
        except KeyError as exc:
            raise KeyError(f"Tanimsiz Inspector alani: {field}") from exc
