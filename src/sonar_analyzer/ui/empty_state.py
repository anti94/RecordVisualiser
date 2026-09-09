"""Boş çalışma alanı yönlendirmesi — `F1-033`.

Kayıt açılmadan merkez alan boş kalmaz: kullanıcıya **ne yapabileceği** söylenir.
Plan Bölüm 5.3: boş workspace'te dosya açma ve kanal ekleme eylemleri görünür
olmalıdır.

Buradaki düğmeler kendi işlerini yapmaz; ana penceredeki eylemleri tetikler.
Böylece aynı iş için iki ayrı yol oluşmaz.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

TITLE = "Baslamak icin bir kayit acin"
HINT = (
    "Bir .bin dosyasi acin veya simulasyon verisiyle deneyin. "
    "Kayit acildiktan sonra soldaki agactan bir kanala cift tiklayarak grafige ekleyin."
)
OPEN_BUTTON_TEXT = "Open .bin File"
SIMULATION_BUTTON_TEXT = "Load Simulation Data"
CHANNEL_HINT = "Kanal eklemek icin: Data Explorer > kanala cift tikla"


class EmptyStatePanel(QWidget):
    """Kayıt açılmadan merkez alanda duran yönlendirme."""

    open_requested = Signal()
    simulation_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel_empty_state")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)

        self.title = QLabel(TITLE, self)
        self.title.setObjectName("label_empty_title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setMinimumWidth(1)
        layout.addWidget(self.title)

        self.hint = QLabel(HINT, self)
        self.hint.setObjectName("label_empty_hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        self.hint.setMinimumWidth(1)
        layout.addWidget(self.hint)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        self.open_button = QPushButton(OPEN_BUTTON_TEXT, self)
        self.open_button.setObjectName("button_empty_open")
        self.open_button.clicked.connect(self.open_requested.emit)
        buttons.addWidget(self.open_button)

        self.simulation_button = QPushButton(SIMULATION_BUTTON_TEXT, self)
        self.simulation_button.setObjectName("button_empty_simulation")
        self.simulation_button.clicked.connect(self.simulation_requested.emit)
        buttons.addWidget(self.simulation_button)

        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.channel_hint = QLabel(CHANNEL_HINT, self)
        self.channel_hint.setObjectName("label_empty_channel_hint")
        self.channel_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.channel_hint.setWordWrap(True)
        self.channel_hint.setMinimumWidth(1)
        layout.addWidget(self.channel_hint)

        layout.addStretch(1)

    def visible_actions(self) -> list[str]:
        """Kullanıcıya sunulan eylem metinleri — kabul kontrolü için."""
        return [self.open_button.text(), self.simulation_button.text()]
