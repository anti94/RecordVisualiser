"""Inspector paneli — bağlamsal araç sekmesi içeriği (`F1-025`).

Plan Bölüm 5.1: *"Inspector, kanal veya olay seçimiyle açılan bağlamsal araç
sekmesidir; sağ sütundaki BIT, Analysis Tools ve Data Export kartlarının yerini
**kalıcı olarak almaz**."*

Bu sınıf yalnız içeriktir; sekme olarak açılıp kapanması
`ui/docks/right_column.py` içindedir.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.raw_record import SampleInspection

PANEL_OBJECT_NAME = "panel_inspector"

#: `F3-040` geliştirici ham görünümü alanları.
RAW_FIELDS: tuple[str, ...] = ("Source offset", "Raw value", "Scaled value", "Sample time")

#: `F3-036` Display sekmesindeki eksen seçenekleri (etiket -> PlotPanel ekseni).
AXIS_CHOICES: tuple[tuple[str, str], ...] = (("Left axis", "left"), ("Right axis", "right"))
_AXIS_LIMIT = 1_000_000_000.0

EMPTY_VALUE = "—"
EMPTY_HINT = "Ayrinti icin bir kanal veya olay secin."

#: Kanal secildiginde gosterilen alanlar (`F3-035`: `ID` eklendi).
CHANNEL_FIELDS = (
    "ID",
    "Channel",
    "Path",
    "Unit",
    "Sample rate",
    "Data type",
    "Source",
    "Time base",
)


class InspectorPanel(QWidget):
    """Seçili kanalın ayrıntısını gösteren bağlamsal panel."""

    #: `F3-036` Display: bir eksenin min/max aralığı elle istendi
    #: (`"left"`/`"right"`, y_min, y_max). MainWindow bunu seçili grafiğe uygular.
    axis_range_requested = Signal(str, float, float)

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

        layout.addWidget(self._build_display_group(body))
        layout.addWidget(self._build_raw_group(body))
        layout.addStretch(1)

    def _build_raw_group(self, parent: QWidget) -> QWidget:
        """`F3-040` Raw: seçilen örneğin kaynak offseti + ham/ölçeklenmiş değeri."""
        group = QGroupBox("Raw (developer)", parent)
        group.setObjectName("group_inspector_raw")
        form = QFormLayout(group)
        form.setContentsMargins(6, 4, 6, 4)
        self._raw_fields: dict[str, QLabel] = {}
        for field in RAW_FIELDS:
            value = QLabel(EMPTY_VALUE, group)
            value.setObjectName(f"label_inspector_raw_{field.lower().replace(' ', '_')}")
            value.setWordWrap(True)
            value.setMinimumWidth(1)
            self._raw_fields[field] = value
            form.addRow(f"{field}:", value)
        return group

    def show_raw_sample(self, inspection: SampleInspection, unit: str = "") -> None:
        """Seçilen örneğin ham kayıt ayrıntısını gösterir — `F3-040`."""
        suffix = f" {unit}" if unit else ""
        self._raw_fields["Source offset"].setText(
            f"{inspection.byte_offset} (0x{inspection.byte_offset:X})"
        )
        self._raw_fields["Raw value"].setText(f"{inspection.raw_value:g}")
        self._raw_fields["Scaled value"].setText(f"{inspection.scaled_value:g}{suffix}")
        self._raw_fields["Sample time"].setText(f"{inspection.timestamp_ns} ns")

    def clear_raw_sample(self) -> None:
        for label in self._raw_fields.values():
            label.setText(EMPTY_VALUE)

    def raw_field_value(self, field: str) -> str:
        try:
            return self._raw_fields[field].text()
        except KeyError as exc:
            raise KeyError(f"Tanimsiz Raw alani: {field}") from exc

    def _build_display_group(self, parent: QWidget) -> QWidget:
        """`F3-036` Display: eksen seçimi + Y min/max, seçili grafiğe uygulanır."""
        group = QGroupBox("Display", parent)
        group.setObjectName("group_inspector_display")
        form = QFormLayout(group)
        form.setContentsMargins(6, 4, 6, 4)

        self.axis_combo = QComboBox(group)
        self.axis_combo.setObjectName("combo_inspector_axis")
        for label, value in AXIS_CHOICES:
            self.axis_combo.addItem(label, value)
        form.addRow("Axis:", self.axis_combo)

        self.y_min_spin = self._make_spin(group, "spin_inspector_y_min", -1.0)
        self.y_max_spin = self._make_spin(group, "spin_inspector_y_max", 1.0)
        form.addRow("Y min:", self.y_min_spin)
        form.addRow("Y max:", self.y_max_spin)

        self.apply_button = QPushButton("Apply", group)
        self.apply_button.setObjectName("button_inspector_apply_display")
        self.apply_button.clicked.connect(self._emit_axis_range)
        form.addRow(self.apply_button)
        return group

    @staticmethod
    def _make_spin(parent: QWidget, name: str, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(parent)
        spin.setObjectName(name)
        spin.setRange(-_AXIS_LIMIT, _AXIS_LIMIT)
        spin.setDecimals(4)
        spin.setValue(value)
        return spin

    def _emit_axis_range(self) -> None:
        y_min = self.y_min_spin.value()
        y_max = self.y_max_spin.value()
        if y_min >= y_max:
            return  # gecersiz aralik sessizce yok sayilir
        axis = str(self.axis_combo.currentData())
        self.axis_range_requested.emit(axis, y_min, y_max)

    def clear(self) -> None:
        """Seçim yokken boş duruma döner."""
        for label in self._fields.values():
            label.setText(EMPTY_VALUE)
        self.clear_raw_sample()
        self.detail.setVisible(False)
        self.hint.setVisible(True)

    def show_channel(self, channel: ChannelMetadata) -> None:
        """Seçilen kanalın ayrıntısını gösterir."""
        rate = (
            f"{channel.sample_rate_hz:g} Hz" if channel.sample_rate_hz is not None else EMPTY_VALUE
        )
        values = {
            "ID": channel.id,
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
