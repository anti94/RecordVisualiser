"""Basit formül editörü — `F4-073`.

Analysis Tools kartının "Custom" sekmesinde, işlem listesi editörünün
altında durur. Kullanıcı `ch0 * 2 - ch1` gibi bir ifade ve bir ad yazar;
geçerliyse bir **türetilmiş kanal tanımı** (`F4-068`) üretilir ve
`definition_requested` ile yayılır.

Doğrulama her tuş vuruşunda çalışır ve `F4-070` ayrıştırıcısını kullanır;
hata metni **ilgili alanın** hemen altında görünür (ifade hatası ifade
alanında, ad hatası ad alanında). Ekleme düğmesi yalnız her iki alan da
geçerliyken etkindir — kullanıcı geçersiz bir tanımı hiç gönderemez.

Bu widget hiçbir şey hesaplamaz ve hiçbir şey çalıştırmaz: ayrıştırma
`F4-070`'in, değerlendirme `F4-071`'in, kanalı eklemek `F4-069`
repository'sinin işidir.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.analysis.formula import Formula, FormulaError, parse_formula
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.derived_channel_definition import (
    DerivedChannelDefinition,
    DerivedChannelError,
)

GROUP_TITLE = "Formül"
PLACEHOLDER = "ör. ch0 * 2 - ch1"
NAME_PLACEHOLDER = "Türetilmiş kanal adı"
ERROR_STYLE = "color: #EF5B5B;"
#: Boş ifade "hata" değildir; kullanıcı henüz yazmaya başlamamıştır.
EMPTY_HINT = "Kullanılabilir kanal yok; önce bir kayıt açın."
#: İfade ayrıştırılıyor ama hiçbir kanala bakmıyor.
NO_CHANNEL_MESSAGE = "Formül en az bir kanala bakmalı; sabitten kanal türetilemez."
#: İfade hazır ama ad boş.
NAME_REQUIRED_MESSAGE = "Türetilmiş kanal için bir ad girin."


class FormulaEditor(QWidget):
    """İfade + ad alanı, alan içi hata ve `Türetilmiş kanal ekle` düğmesi."""

    #: Geçerli bir tanım hazır ve kullanıcı eklemek istedi.
    definition_requested = Signal(object)
    #: Doğrulama durumu değişti (geçerli mi).
    validity_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel_formula_editor")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 6, 0, 0)

        group = QGroupBox(GROUP_TITLE, self)
        group.setObjectName("group_formula")
        form = QFormLayout(group)
        form.setContentsMargins(6, 6, 6, 6)

        self.expression_input = QLineEdit(group)
        self.expression_input.setObjectName("input_formula_expression")
        self.expression_input.setPlaceholderText(PLACEHOLDER)
        form.addRow("İfade", self.expression_input)

        self.expression_error = QLabel(group)
        self.expression_error.setObjectName("label_formula_expression_error")
        self.expression_error.setWordWrap(True)
        self.expression_error.setStyleSheet(ERROR_STYLE)
        self.expression_error.hide()
        form.addRow("", self.expression_error)

        self.name_input = QLineEdit(group)
        self.name_input.setObjectName("input_formula_name")
        self.name_input.setPlaceholderText(NAME_PLACEHOLDER)
        form.addRow("Ad", self.name_input)

        self.name_error = QLabel(group)
        self.name_error.setObjectName("label_formula_name_error")
        self.name_error.setWordWrap(True)
        self.name_error.setStyleSheet(ERROR_STYLE)
        self.name_error.hide()
        form.addRow("", self.name_error)

        self.channels_hint = QLabel(EMPTY_HINT, group)
        self.channels_hint.setObjectName("label_formula_channels")
        self.channels_hint.setWordWrap(True)
        form.addRow("", self.channels_hint)

        self.add_button = QPushButton("Türetilmiş kanal ekle", group)
        self.add_button.setObjectName("button_formula_add")
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self._on_add)
        form.addRow(self.add_button)

        outer.addWidget(group)

        self._aliases: dict[str, str] = {}
        self._formula: Formula | None = None
        self._valid = False

        self.expression_input.textChanged.connect(self._revalidate)
        self.name_input.textChanged.connect(self._revalidate)
        self._revalidate()

    # -- kullanilabilir kanallar -------------------------------------------

    def set_channels(self, channels: list[ChannelMetadata]) -> None:
        """Formülde yazılabilecek kanalları belirler.

        Kanal kimliği geçerli bir tanımlayıcıysa kendi adıyla yazılır;
        değilse (`derived:ab12`) formülde kullanılamaz ve ipucunda
        listelenmez — takma ad desteği ayrı bir iştir.
        """
        self._aliases = {
            channel.id: channel.id for channel in channels if channel.id.isidentifier()
        }
        self.channels_hint.setText(
            "Kullanılabilir: " + ", ".join(sorted(self._aliases)) if self._aliases else EMPTY_HINT
        )
        self._revalidate()

    def available_names(self) -> list[str]:
        return sorted(self._aliases)

    # -- durum -------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """İfade **ve** ad geçerli mi (düğmenin etkinliğiyle aynı)."""
        return self._valid

    def formula(self) -> Formula | None:
        """Son geçerli ayrıştırma; ifade geçersizse `None`."""
        return self._formula

    def expression_error_text(self) -> str:
        """Görünen ifade hatası; hata yoksa boş metin.

        `isHidden()` kullanılır, `isVisible()` değil: pencere henüz
        gösterilmemişken tüm çocuklar "görünmez"dir ama gizlenmiş
        olmaları ayrı bir şeydir.
        """
        return "" if self.expression_error.isHidden() else self.expression_error.text()

    def name_error_text(self) -> str:
        """Görünen ad hatası; hata yoksa boş metin."""
        return "" if self.name_error.isHidden() else self.name_error.text()

    def definition(self) -> DerivedChannelDefinition | None:
        """O anki alanlardan üretilen tanım; geçersizse `None`."""
        if not self._valid or self._formula is None:
            return None
        try:
            return DerivedChannelDefinition(
                name=self.name_input.text().strip(),
                inputs=self._formula.channel_ids,
                expression=self._formula.text,
            )
        except DerivedChannelError:  # pragma: no cover - dogrulama zaten engeller
            return None

    def set_expression(self, text: str) -> None:
        self.expression_input.setText(text)

    def set_name(self, text: str) -> None:
        self.name_input.setText(text)

    # -- dogrulama ---------------------------------------------------------

    def _revalidate(self) -> None:
        """Her tuş vuruşunda çalışır; hatayı **ilgili** alanın altına yazar."""
        expression = self.expression_input.text().strip()
        self._formula = None
        expression_message = ""
        if expression:
            try:
                candidate = parse_formula(expression, self._aliases)
            except FormulaError as exc:
                expression_message = str(exc)
            else:
                if candidate.channel_ids:
                    self._formula = candidate
                else:
                    # Kanalsız bir ifade türetilmiş kanal olamaz; bu ifadenin
                    # sorunudur, adın değil.
                    expression_message = NO_CHANNEL_MESSAGE
        self._show(self.expression_error, expression_message)

        # Ad hatası yalnız ifade hazırken anlamlıdır; yoksa kullanıcı daha
        # yazmaya başlamadan kırmızı bir uyarı görürdü.
        name_message = ""
        if self._formula is not None and not self.name_input.text().strip():
            name_message = NAME_REQUIRED_MESSAGE
        self._show(self.name_error, name_message)

        valid = self._formula is not None and not name_message
        self.add_button.setEnabled(valid)
        if valid != self._valid:
            self._valid = valid
            self.validity_changed.emit(valid)

    @staticmethod
    def _show(label: QLabel, message: str) -> None:
        label.setText(message)
        label.setVisible(bool(message))

    # -- gonderme ----------------------------------------------------------

    def _on_add(self) -> None:
        definition = self.definition()
        if definition is not None:
            self.definition_requested.emit(definition)
