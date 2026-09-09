"""Koyu tema ve mavi vurgular — `F1-029`.

Renk tokenları plan Bölüm 6.2'den gelir. Tokenlar **tek yerde** tanımlıdır;
stil sayfası bunlardan üretilir. Bir rengi doğrudan widget içine yazmak
yasaktır — aksi hâlde tema değiştiğinde bazı yüzeyler eski renkte kalır.

Kontrast, plan Bölüm 6.4 gereği ölçülebilir olmalıdır: `contrast_ratio`
WCAG 2.x bağıl parlaklık formülünü uygular ve testler ana metin için 4.5:1
eşiğini denetler.
"""

from __future__ import annotations

from dataclasses import dataclass


def _channel(value: str) -> float:
    """sRGB bileşenini bağıl parlaklık için doğrusallaştırır."""
    c = int(value, 16) / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG bağıl parlaklığı (0 = siyah, 1 = beyaz)."""
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Renk #RRGGBB olmali, verilen: {hex_color!r}")
    red, green, blue = value[0:2], value[2:4], value[4:6]
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(first: str, second: str) -> float:
    """İki renk arasındaki WCAG kontrast oranı (1.0 – 21.0)."""
    light = relative_luminance(first)
    dark = relative_luminance(second)
    if light < dark:
        light, dark = dark, light
    return (light + 0.05) / (dark + 0.05)


@dataclass(frozen=True)
class Palette:
    """Plan Bölüm 6.2 tokenları."""

    background: str = "#0B1118"
    surface: str = "#121B24"
    surface_elevated: str = "#182430"
    border: str = "#2B3A48"
    text_primary: str = "#E6EDF3"
    text_secondary: str = "#94A3B8"
    accent: str = "#1689F5"
    pass_: str = "#39C77A"
    warning: str = "#F2B84B"
    error: str = "#EF5B5B"
    critical: str = "#D946EF"

    @property
    def on_accent(self) -> str:
        """Vurgu zemini üzerine yazılacak metin rengi.

        Beyaz ile koyu arka plandan **hangisi daha yüksek kontrast veriyorsa**
        o seçilir; sabit beyaz yazmak parlak bir vurgu renginde 4.5:1 eşiğinin
        altına düşüyordu. Palet değişince seçim de değişir.
        """
        white = "#FFFFFF"
        return (
            white
            if contrast_ratio(white, self.accent) > contrast_ratio(self.background, self.accent)
            else self.background
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "background": self.background,
            "surface": self.surface,
            "surface_elevated": self.surface_elevated,
            "border": self.border,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "accent": self.accent,
            "pass": self.pass_,
            "warning": self.warning,
            "error": self.error,
            "critical": self.critical,
        }


DARK = Palette()

#: Ontanimli temada vurgu zemini uzerindeki metin rengi.
#: #FFFFFF ile #1689F5 kontrasti 3.54:1 (esik 4.5:1); koyu arka plan 5.35:1 verir.
ON_ACCENT = DARK.on_accent

#: Grafik kanallari icin sabit palet. XYZ icin mavi/turuncu/yesil (plan 5.1).
#: Ayni kanal calisma alani boyunca ayni rengi korur (plan 6.3).
CHANNEL_COLORS: tuple[str, ...] = (
    "#4C9AFF",  # X - mavi
    "#F2994A",  # Y - turuncu
    "#39C77A",  # Z - yesil
    "#D946EF",
    "#F2B84B",
    "#22C7C7",
    "#EF5B5B",
    "#A78BFA",
)


def build_stylesheet(palette: Palette = DARK) -> str:
    """Tokenlardan Qt stil sayfası üretir."""
    p = palette
    return f"""
QMainWindow, QWidget {{
    background-color: {p.background};
    color: {p.text_primary};
}}
QDockWidget {{
    color: {p.text_primary};
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background-color: {p.surface_elevated};
    padding: 4px 8px;
    border: 1px solid {p.border};
}}
QDockWidget > QWidget {{
    background-color: {p.surface};
}}
QGroupBox {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {p.text_secondary};
}}
QTabWidget::pane {{
    border: 1px solid {p.border};
    background-color: {p.surface};
}}
QTabBar::tab {{
    background-color: {p.surface};
    color: {p.text_secondary};
    border: 1px solid {p.border};
    padding: 4px 12px;
}}
QTabBar::tab:selected {{
    background-color: {p.surface_elevated};
    color: {p.text_primary};
    border-bottom: 2px solid {p.accent};
}}
QTabBar::tab:hover {{
    background-color: {p.surface_elevated};
}}
QPushButton {{
    background-color: {p.surface_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
    border-radius: 3px;
    padding: 4px 10px;
}}
QPushButton:hover {{
    border-color: {p.accent};
}}
QPushButton:checked {{
    background-color: {p.accent};
    color: {p.background};
}}
QPushButton:disabled {{
    color: {p.text_secondary};
    border-color: {p.border};
}}
QPushButton#button_open_bin {{
    background-color: {p.accent};
    color: {p.on_accent};
    font-weight: bold;
    /* Sol sutun 200 px; genis dolgu panelin asgari genisligini bu sinirin
       uzerine cikariyordu. */
    padding: 4px 6px;
}}
QLineEdit, QDoubleSpinBox, QComboBox {{
    background-color: {p.background};
    color: {p.text_primary};
    border: 1px solid {p.border};
    border-radius: 3px;
    padding: 3px 6px;
    selection-background-color: {p.accent};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {p.accent};
}}
QTreeWidget, QTableWidget, QPlainTextEdit {{
    background-color: {p.surface};
    alternate-background-color: {p.surface_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
    selection-background-color: {p.accent};
    selection-color: {p.on_accent};
}}
QHeaderView::section {{
    background-color: {p.surface_elevated};
    color: {p.text_secondary};
    border: none;
    border-bottom: 1px solid {p.border};
    padding: 4px;
}}
QMenuBar {{
    background-color: {p.surface};
    color: {p.text_primary};
}}
QMenuBar::item:selected {{
    background-color: {p.accent};
    color: {p.on_accent};
}}
QMenu {{
    background-color: {p.surface_elevated};
    color: {p.text_primary};
    border: 1px solid {p.border};
}}
QMenu::item:selected {{
    background-color: {p.accent};
    color: {p.on_accent};
}}
QMenu::item:disabled {{
    color: {p.text_secondary};
}}
QToolBar {{
    background-color: {p.surface};
    border-bottom: 1px solid {p.border};
    spacing: 4px;
}}
QStatusBar {{
    background-color: {p.surface};
    color: {p.text_secondary};
    border-top: 1px solid {p.border};
}}
QStatusBar QLabel {{
    color: {p.text_secondary};
}}
QSlider::groove:horizontal {{
    background: {p.border};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {p.accent};
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QProgressBar {{
    background-color: {p.background};
    border: 1px solid {p.border};
    border-radius: 3px;
}}
QProgressBar::chunk {{
    background-color: {p.accent};
}}
QSplitter::handle {{
    background-color: {p.border};
}}
""".strip()


def apply_theme(target: object, palette: Palette = DARK) -> None:
    """Stil sayfasını uygulama veya pencereye uygular."""
    setter = getattr(target, "setStyleSheet", None)
    if not callable(setter):
        raise TypeError("Hedef setStyleSheet desteklemiyor")
    setter(build_stylesheet(palette))
