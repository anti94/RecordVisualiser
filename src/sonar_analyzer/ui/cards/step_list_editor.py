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

from typing import Union, cast

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import (
    MAX_MOVING_AVERAGE_WINDOW,
    PARAMETER_SPECS,
    ProcessingStep,
    StepKind,
    StepValidationError,
)
from sonar_analyzer.processing.windowing import (
    WindowingError,
    duration_for_samples,
    samples_for_duration,
)

#: Parametre alanı geniş aralık: politika dışı değer de girilip
#: **açıklanabilsin** diye (`F4-007`).
_FLOAT_RANGE = (-1.0e9, 1.0e9)
_INT_RANGE = (-1000, 1_000_000)

#: Bazı tam sayı parametreleri kendi aralığını ister. `window` için üst
#: sınır, "aşırı pencere"nin girilip **açıklanabilmesi** için modelin
#: kabul ettiği en büyük değerin biraz üstündedir (`F4-018`); alt sınır
#: sıfır ve negatifin de girilip reddedilebilmesi için negatiftir.
_INT_RANGE_BY_PARAM: dict[str, tuple[int, int]] = {
    "window": (-1000, MAX_MOVING_AVERAGE_WINDOW + 1000),
}

#: Combobox'ta gösterilen sıra.
STEP_KIND_ORDER: tuple[StepKind, ...] = (
    StepKind.SCALE,
    StepKind.OFFSET,
    StepKind.ABS,
    StepKind.CLIP,
    StepKind.MOVING_AVERAGE,
    StepKind.DETREND,
    StepKind.NORMALIZE,
    StepKind.WINDOWED_RMS,
    StepKind.ENVELOPE,
    StepKind.PHASE_UNWRAP,
)

#: `window` parametresi bir **süre** (saniye) olarak sunulan ve kanalın
#: sample rate'i üzerinden örnek sayısına çevrilen işlem türleri (`F4-022`).
#: `MOVING_AVERAGE` hariç: onun penceresi ham örnek sayısıdır (`F4-018`).
_DURATION_WINDOW_KINDS: frozenset[StepKind] = frozenset({StepKind.WINDOWED_RMS, StepKind.ENVELOPE})

#: Süre alanı sınırları (saniye).
_DURATION_RANGE_S = (0.0, 3600.0)

#: Bir parametre alanı widget'ı. `ParamSpec.choices` dolu str parametreler
#: (örn. `DETREND.mode`) açılır liste, sayısal parametreler spin box olur.
ParamField = Union[QDoubleSpinBox, QSpinBox, QComboBox]


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
        self._sample_rate_hz = 0.0
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

        # F4-007: seçili adımın parametreleri + alan içi hata açıklaması.
        self.param_panel = QWidget(self)
        self.param_panel.setObjectName("panel_step_params")
        self.param_form = QFormLayout(self.param_panel)
        self.param_form.setContentsMargins(0, 4, 0, 0)
        layout.addWidget(self.param_panel)

        self.param_error = QLabel(self)
        self.param_error.setObjectName("label_param_error")
        self.param_error.setWordWrap(True)
        self.param_error.setStyleSheet("color: #EF5B5B;")
        self.param_error.hide()
        layout.addWidget(self.param_error)

        self._param_fields: dict[str, ParamField] = {}
        #: Değeri **saniye** tutan ve modele örnek sayısı olarak çevrilen
        #: parametre alanlarının adları (`F4-022`).
        self._duration_fields: set[str] = set()
        self._suppress_param_signal = False
        self._error_active = False

        self._refresh_buttons()
        self._rebuild_param_panel(None)

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

    def set_sample_rate(self, sample_rate_hz: float) -> None:
        """Süre tabanlı pencere alanları için kanal sample rate'i (`F4-022`).

        0 (ya da bilinmeyen) verilirse süre alanları yerine ham örnek
        sayısı spin box'ı gösterilir.
        """
        new_rate = max(float(sample_rate_hz), 0.0)
        if new_rate == self._sample_rate_hz:
            return
        self._sample_rate_hz = new_rate
        row = self.list.currentRow()
        self._rebuild_param_panel(self._steps[row] if 0 <= row < len(self._steps) else None)

    @property
    def sample_rate_hz(self) -> float:
        return self._sample_rate_hz

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
        row = self.list.currentRow()
        self._rebuild_param_panel(self._steps[row] if 0 <= row < len(self._steps) else None)

    # -- parametre paneli (F4-007) ----------------------------

    def parameter_error(self) -> str:
        """Alan içi hata metni; hata yoksa boş — testler ve kabul için."""
        return self.param_error.text() if self._error_active else ""

    @property
    def has_parameter_error(self) -> bool:
        return self._error_active

    def _set_param_error(self, message: str) -> None:
        self._error_active = bool(message)
        self.param_error.setText(message)
        self.param_error.setVisible(self._error_active)

    def param_field_names(self) -> list[str]:
        """Seçili adım için gösterilen parametre alanlarının adları."""
        return list(self._param_fields)

    def param_field(self, name: str) -> ParamField:
        """Bir parametre alanı widget'ı — testler ve kabul için."""
        return self._param_fields[name]

    def set_param_field(self, name: str, value: float | str) -> None:
        """Bir parametre alanının değerini ayarlar (alan tipine göre)."""
        field = self._param_fields[name]
        if isinstance(field, QComboBox):
            index = field.findData(value)
            if index < 0:
                index = field.findText(str(value))
            if index >= 0:
                field.setCurrentIndex(index)
        elif isinstance(field, QSpinBox):
            field.setValue(int(value))
        else:
            field.setValue(float(value))

    def param_value(self, name: str) -> object:
        """Bir parametre alanının o anki değeri (alan tipinden bağımsız) — testler için."""
        return self._field_value(self._param_fields[name])

    @staticmethod
    def _field_value(field: ParamField) -> object:
        """Alan tipinden bağımsız olarak o anki değeri döndürür."""
        if isinstance(field, QComboBox):
            return field.currentData()
        return field.value()

    def _rebuild_param_panel(self, step: ProcessingStep | None) -> None:
        self._suppress_param_signal = True
        while self.param_form.rowCount():
            self.param_form.removeRow(0)
        self._param_fields = {}
        self._duration_fields = set()
        self._set_param_error("")

        if step is None:
            self.param_panel.setVisible(False)
            self._suppress_param_signal = False
            return
        self.param_panel.setVisible(True)

        want_duration = step.kind in _DURATION_WINDOW_KINDS and self._sample_rate_hz > 0.0

        for spec in PARAMETER_SPECS[step.kind]:
            value = step.parameters[spec.name]
            field: ParamField
            if spec.choices:
                field = QComboBox(self.param_panel)
                for choice in spec.choices:
                    field.addItem(str(choice), choice)
                index = field.findData(value)
                field.setCurrentIndex(index if index >= 0 else 0)
                field.currentIndexChanged.connect(self._on_param_edit)
            elif want_duration and spec.name == "window":
                field = QDoubleSpinBox(self.param_panel)
                field.setRange(*_DURATION_RANGE_S)
                field.setDecimals(4)
                field.setSuffix(" s")
                samples = int(value) if isinstance(value, (int, float)) else 1
                field.setValue(duration_for_samples(samples, self._sample_rate_hz))
                field.valueChanged.connect(self._on_param_edit)
                self._duration_fields.add(spec.name)
            elif spec.kind is int:
                field = QSpinBox(self.param_panel)
                field.setRange(*_INT_RANGE_BY_PARAM.get(spec.name, _INT_RANGE))
                field.setValue(int(value) if isinstance(value, (int, float)) else 0)
                field.valueChanged.connect(self._on_param_edit)
            else:
                field = QDoubleSpinBox(self.param_panel)
                field.setRange(*_FLOAT_RANGE)
                field.setDecimals(4)
                field.setValue(float(value) if isinstance(value, (int, float)) else 0.0)
                field.valueChanged.connect(self._on_param_edit)
            field.setObjectName(f"field_param_{spec.name}")
            self._param_fields[spec.name] = field
            self.param_form.addRow(spec.name, field)

        self._suppress_param_signal = False

    def _on_param_edit(self) -> None:
        """Alan değişince adımı **işlem başlamadan** doğrular; hatayı gösterir."""
        if self._suppress_param_signal:
            return
        row = self.list.currentRow()
        if not 0 <= row < len(self._steps):
            return
        old = self._steps[row]
        params: dict[str, object] = {}
        for name, fld in self._param_fields.items():
            raw = self._field_value(fld)
            if name in self._duration_fields:
                seconds = float(cast("float", raw)) if isinstance(raw, (int, float)) else 0.0
                try:
                    params[name] = samples_for_duration(seconds, self._sample_rate_hz)
                except WindowingError as exc:
                    self._set_param_error(str(exc))
                    return
            else:
                params[name] = raw
        try:
            new_step = ProcessingStep(
                kind=old.kind,
                input_channel_id=old.input_channel_id,
                parameters=params,
                enabled=old.enabled,
            )
        except StepValidationError as exc:
            self._set_param_error(str(exc))
            return
        self._set_param_error("")
        self._steps[row] = new_step
        item = self.list.item(row)
        if item is not None:
            item.setText(step_label(new_step))
        self.chain_changed.emit()

    def _refresh_buttons(self) -> None:
        row = self.list.currentRow()
        has_selection = 0 <= row < len(self._steps)
        self.add_button.setEnabled(bool(self._input_channel_id))
        self.remove_button.setEnabled(has_selection)
        self.up_button.setEnabled(has_selection and row > 0)
        self.down_button.setEnabled(has_selection and row < len(self._steps) - 1)
