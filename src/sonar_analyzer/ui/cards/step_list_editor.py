"""İşlem listesi editörü — `F4-006`.

Analysis Tools kartının "Custom" sekmesinde durur. Kullanıcı DSP
adımlarını ekler, siler ve yeniden sıralar; editörün durumu birebir bir
`ProcessingChain`'e karşılık gelir (`chain()` / `set_chain()`). Her
düzenleme `chain_changed` yayar — önizleme/uygula sonraki işlerde
(`F4-007`+) buna bağlanır.

Adım eklerken kullanılan girdi kanalı `set_input_channel(id)` ile
verilir; verilmemişse yeni adım eklenemez (buton pasif).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import PARAMETER_SPECS, ProcessingStep, StepKind

#: Combobox'ta gösterilen sıra.
STEP_KIND_ORDER: tuple[StepKind, ...] = (
    StepKind.SCALE,
    StepKind.OFFSET,
    StepKind.ABS,
    StepKind.CLIP,
    StepKind.MOVING_AVERAGE,
)


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:g}"
    return str(value)


def step_label(step: ProcessingStep) -> str:
    """Liste satırı metni: işlem türü + anahtar parametreler."""
    params = ", ".join(
        f"{spec.name}={_format_value(step.parameters[spec.name])}"
        for spec in PARAMETER_SPECS[step.kind]
    )
    prefix = "" if step.enabled else "(kapalı) "
    return f"{prefix}{step.kind.value}" + (f" · {params}" if params else "")


class StepListEditor(QWidget):
    """DSP işlem zincirini görsel olarak düzenleyen liste editörü."""

    #: Zincir her değiştiğinde (ekle / sil / taşı / kanal) yayılır.
    chain_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("editor_step_list")
        self._input_channel_id = ""
        self._steps: list[ProcessingStep] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        add_row = QHBoxLayout()
        self.kind_selector = QComboBox(self)
        self.kind_selector.setObjectName("combo_step_kind")
        for kind in STEP_KIND_ORDER:
            self.kind_selector.addItem(kind.value, kind)
        add_row.addWidget(self.kind_selector, 1)

        self.add_button = QPushButton("Ekle", self)
        self.add_button.setObjectName("button_step_add")
        self.add_button.clicked.connect(self._on_add)
        add_row.addWidget(self.add_button)
        layout.addLayout(add_row)

        self.list = QListWidget(self)
        self.list.setObjectName("list_steps")
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.list, 1)

        button_row = QHBoxLayout()
        self.up_button = QPushButton("Yukarı", self)
        self.up_button.setObjectName("button_step_up")
        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button = QPushButton("Aşağı", self)
        self.down_button.setObjectName("button_step_down")
        self.down_button.clicked.connect(lambda: self._move(1))
        self.remove_button = QPushButton("Sil", self)
        self.remove_button.setObjectName("button_step_remove")
        self.remove_button.clicked.connect(self._on_remove)
        for widget in (self.up_button, self.down_button, self.remove_button):
            button_row.addWidget(widget)
        layout.addLayout(button_row)

        self._refresh_buttons()

    # -- model köprüsü -----------------------------------------

    def chain(self) -> ProcessingChain:
        """Editörün o anki durumuna karşılık gelen zincir."""
        return ProcessingChain(list(self._steps))

    def set_chain(self, chain: ProcessingChain) -> None:
        """Bir zinciri editöre yükler (sinyal yaymaz)."""
        self._steps = list(chain.steps)
        self._rebuild_list()

    def step_count(self) -> int:
        return len(self._steps)

    def set_input_channel(self, channel_id: str) -> None:
        self._input_channel_id = channel_id
        self._refresh_buttons()

    # -- düzenleme -------------------------------------------

    def _on_add(self) -> None:
        if not self._input_channel_id:
            return
        data = self.kind_selector.currentData()
        kind = data if isinstance(data, StepKind) else StepKind(str(data))
        self._steps.append(ProcessingStep.default(kind, self._input_channel_id))
        self._rebuild_list()
        self.list.setCurrentRow(len(self._steps) - 1)
        self.chain_changed.emit()

    def _on_remove(self) -> None:
        row = self.list.currentRow()
        if not 0 <= row < len(self._steps):
            return
        del self._steps[row]
        self._rebuild_list()
        self.list.setCurrentRow(min(row, len(self._steps) - 1))
        self.chain_changed.emit()

    def _move(self, delta: int) -> None:
        row = self.list.currentRow()
        target = row + delta
        if not (0 <= row < len(self._steps) and 0 <= target < len(self._steps)):
            return
        self._steps.insert(target, self._steps.pop(row))
        self._rebuild_list()
        self.list.setCurrentRow(target)
        self.chain_changed.emit()

    # -- ic ------------------------------------------------

    def _rebuild_list(self) -> None:
        self.list.clear()
        for step in self._steps:
            item = QListWidgetItem(step_label(step))
            item.setData(Qt.ItemDataRole.UserRole, step.kind.value)
            self.list.addItem(item)
        self._refresh_buttons()

    def _on_row_changed(self, _row: int) -> None:
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        row = self.list.currentRow()
        has_selection = 0 <= row < len(self._steps)
        self.add_button.setEnabled(bool(self._input_channel_id))
        self.remove_button.setEnabled(has_selection)
        self.up_button.setEnabled(has_selection and row > 0)
        self.down_button.setEnabled(has_selection and row < len(self._steps) - 1)
