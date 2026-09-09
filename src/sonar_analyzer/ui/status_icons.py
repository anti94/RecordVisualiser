"""Durum ikonları ve kanal renkleri — `F1-030`.

Plan Bölüm 6.4: durum **yalnız renkle** anlatılmaz. Her durumun bir simgesi ve
bir metni vardır; renk üçüncü ipucudur. Böylece renk körü kullanıcı ve gri
tonlamalı çıktı da durumu ayırt eder.

Kanal renkleri `ui/theme.py` içindeki sabit paletten gelir ve **kanal kimliğine
göre belirlenir**: aynı kanal, çalışma alanı boyunca aynı rengi korur
(plan Bölüm 6.3).
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from sonar_analyzer.domain.event import BitState, Severity
from sonar_analyzer.ui.theme import CHANNEL_COLORS, DARK

ICON_SIZE = 14


@dataclass(frozen=True)
class StatusStyle:
    """Bir durumun simgesi, metni ve rengi."""

    symbol: str
    label: str
    color: str

    def describe(self) -> str:
        """Simge ve metni birlikte verir; renge bağlı kalmaz."""
        return f"{self.symbol} {self.label}"


#: BIT durumlari (docs/format/profile-a.md §5.2).
BIT_STYLES: dict[BitState, StatusStyle] = {
    BitState.PASS: StatusStyle("✓", "OK", DARK.pass_),
    BitState.WARN: StatusStyle("!", "Warning", DARK.warning),
    BitState.FAIL: StatusStyle("✕", "Fail", DARK.error),
    BitState.NOT_RUN: StatusStyle("–", "Not run", DARK.text_secondary),
    BitState.UNKNOWN: StatusStyle("?", "Unknown", DARK.text_secondary),
}

#: Olay siddetleri.
SEVERITY_STYLES: dict[Severity, StatusStyle] = {
    Severity.INFO: StatusStyle("i", "Info", DARK.text_secondary),
    Severity.WARNING: StatusStyle("!", "Warning", DARK.warning),
    Severity.ERROR: StatusStyle("✕", "Error", DARK.error),
    Severity.CRITICAL: StatusStyle("!!", "Critical", DARK.critical),
}


def bit_style(state: BitState) -> StatusStyle:
    """BIT durumunun stili; tanınmayan durum `UNKNOWN` gibi ele alınır."""
    return BIT_STYLES.get(state, BIT_STYLES[BitState.UNKNOWN])


def severity_style(severity: Severity) -> StatusStyle:
    return SEVERITY_STYLES.get(severity, SEVERITY_STYLES[Severity.WARNING])


def channel_color(channel_id: str, index: int | None = None) -> str:
    """Kanalın kalıcı rengi.

    `index` verilirse sıra kullanılır (XYZ için mavi/turuncu/yeşil sırası
    korunur); verilmezse kanal kimliğinden kararlı bir seçim yapılır. Aynı
    girdi her zaman aynı rengi verir.
    """
    if index is not None:
        return CHANNEL_COLORS[index % len(CHANNEL_COLORS)]
    # Yerlesik hash() calisma arasinda degisebilir; kararli olsun diye
    # karakter toplami kullanilir.
    digest = sum(ord(char) for char in channel_id)
    return CHANNEL_COLORS[digest % len(CHANNEL_COLORS)]


def make_status_icon(style: StatusStyle, size: int = ICON_SIZE) -> QIcon:
    """Simgeyi renkli bir daire içinde çizer.

    İkon dosyaya bağımlı değildir; tema rengi değişince yeniden üretilir.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor(style.color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(0.5, 0.5, size - 1.0, size - 1.0))

        font = QFont()
        font.setPixelSize(max(7, size - 5))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(DARK.background))
        painter.drawText(
            QRectF(0, 0, size, size),
            Qt.AlignmentFlag.AlignCenter,
            style.symbol,
        )
    finally:
        painter.end()

    return QIcon(pixmap)
