"""Menü ve toolbar eylemleri — `F1-023`.

Eylemler tek yerde tanımlanır; menü, toolbar ve klavye kısayolları aynı
`QAction` nesnesini paylaşır. Böylece bir eylem devre dışıysa her üç yerde
birden devre dışı olur.

Henüz uygulanmamış analizler **gizlenmez, pasif gösterilir** ve nedeni
ipucunda yazar (plan Bölüm 3.1): işlevi olmayan alanda gerçek sonuç izlenimi
veren sahte çıktı üretilmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

#: Henuz uygulanmamis eylemlerin ipucunda gecen aciklama.
NOT_YET_AVAILABLE = "v2.0.0 ile kullanilabilir"


@dataclass(frozen=True)
class ActionSpec:
    """Tek bir eylemin tanımı."""

    name: str
    text: str
    shortcut: str = ""
    enabled: bool = True
    tooltip: str = ""
    checkable: bool = False
    checked: bool = False


@dataclass(frozen=True)
class MenuSpec:
    """Bir menü ve içindeki eylemler."""

    name: str
    title: str
    actions: tuple[ActionSpec, ...] = field(default_factory=tuple)


#: Plan Bolum 22 F1-023 kabulu: File, View, Analysis, Tools ve Help.
MENU_SPECS: tuple[MenuSpec, ...] = (
    MenuSpec(
        "menu_file",
        "&File",
        (
            ActionSpec("action_open", "Open .bin File...", "Ctrl+O"),
            ActionSpec("action_close", "Close Recording", "Ctrl+W", enabled=False),
            ActionSpec("action_export", "Export Data...", "Ctrl+E", enabled=False),
            ActionSpec("action_exit", "Exit", "Ctrl+Q"),
        ),
    ),
    MenuSpec(
        "menu_view",
        "&View",
        (
            ActionSpec(
                "action_toggle_data_explorer",
                "Data Explorer",
                "Ctrl+1",
                checkable=True,
                checked=True,
            ),
            ActionSpec(
                "action_toggle_right_column",
                "BIT / Analysis / Export",
                "Ctrl+2",
                checkable=True,
                checked=True,
            ),
            ActionSpec("action_reset_layout", "Reset Layout"),
        ),
    ),
    MenuSpec(
        "menu_analysis",
        "&Analysis",
        (
            ActionSpec("action_fft", "FFT", enabled=False, tooltip=NOT_YET_AVAILABLE),
            ActionSpec(
                "action_spectrogram", "Spectrogram", enabled=False, tooltip=NOT_YET_AVAILABLE
            ),
            ActionSpec("action_filter", "Filter...", enabled=False, tooltip=NOT_YET_AVAILABLE),
            ActionSpec("action_statistics", "Statistics", enabled=False, tooltip=NOT_YET_AVAILABLE),
        ),
    ),
    MenuSpec(
        "menu_tools",
        "&Tools",
        (
            ActionSpec("action_settings", "Settings...", "Ctrl+,"),
            ActionSpec("action_diagnostics", "Diagnostics", enabled=False),
        ),
    ),
    MenuSpec(
        "menu_help",
        "&Help",
        (
            ActionSpec("action_documentation", "Documentation"),
            ActionSpec("action_about", "About SONAR Data Analyzer"),
        ),
    ),
)

#: Hizli araclar seridinde gorunecek eylemler (docs/ui/layout-map.md bolge 2).
TOOLBAR_ACTION_NAMES: tuple[str, ...] = (
    "action_open",
    "action_export",
    "action_reset_layout",
    "action_settings",
)


def build_action(parent: QWidget, spec: ActionSpec) -> QAction:
    """Tanımdan `QAction` üretir."""
    action = QAction(spec.text, parent)
    action.setObjectName(spec.name)
    if spec.shortcut:
        action.setShortcut(QKeySequence(spec.shortcut))
    action.setEnabled(spec.enabled)
    action.setCheckable(spec.checkable)
    if spec.checkable:
        action.setChecked(spec.checked)

    tooltip = spec.tooltip
    if not spec.enabled and not tooltip:
        tooltip = "Bu kayit acilmadan kullanilamaz"
    if tooltip:
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
    return action
