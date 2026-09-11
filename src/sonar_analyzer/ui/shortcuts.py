"""Bölüm 16 klavye kısayolları — `F3-072`.

Plan §16 tablosunun temel alt kümesi. Kısayollar iki kapsamda kurulur:

* ``"window"`` — pencere genelinde (dosya işlemleri).
* ``"plot"`` — yalnız **odak merkez grafikteyken** (oynatma, zoom, cursor,
  region, event gezinme). Kabul: "Odak grafikteyken temel dosya,
  oynatma ve zoom kısayolları çalışır".

`install_shortcuts(window)` her satır için bir `QShortcut` oluşturur ve
`activated` sinyalini `window` üzerindeki adı verilen metoda bağlar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

if TYPE_CHECKING:
    from sonar_analyzer.ui.main_window import MainWindow


@dataclass(frozen=True)
class ShortcutSpec:
    """Tek bir kısayol: tuş dizisi, çağrılacak metot, kapsam, açıklama."""

    key: str
    handler: str
    scope: str  # "window" | "plot"
    description: str


#: Plan §16 — uygulanan çekirdek kısayollar.
SHORTCUTS: tuple[ShortcutSpec, ...] = (
    ShortcutSpec("Ctrl+S", "save_workspace_via_dialog", "window", "Workspace kaydet"),
    # F4-079: işlem zinciri ve işaret düzenlemeleri. Görünüm değişikliklerinin
    # (renk, eksen) kendi geçmişi vardır — `F3-041`, Display panelinden.
    ShortcutSpec("Ctrl+Z", "undo_edit", "window", "Düzenlemeyi geri al"),
    ShortcutSpec("Ctrl+Shift+Z", "redo_edit", "window", "Düzenlemeyi yeniden uygula"),
    ShortcutSpec("Space", "toggle_playback", "plot", "Oynat / duraklat"),
    ShortcutSpec("Home", "reset_plot_view", "plot", "Görünümü sıfırla"),
    ShortcutSpec("X", "set_zoom_mode_x", "plot", "X zoom modu"),
    ShortcutSpec("Y", "set_zoom_mode_y", "plot", "Y zoom modu"),
    ShortcutSpec("B", "set_zoom_mode_xy", "plot", "XY zoom modu"),
    ShortcutSpec("C", "toggle_cursor_mode", "plot", "Cursor modu"),
    ShortcutSpec("R", "toggle_region_selection", "plot", "Region selection"),
    ShortcutSpec("F4", "goto_next_event_shortcut", "plot", "Sonraki event"),
    ShortcutSpec("Shift+F4", "goto_previous_event_shortcut", "plot", "Önceki event"),
)


def install_shortcuts(window: MainWindow) -> dict[str, QShortcut]:
    """`SHORTCUTS` tablosunu `window`'a kurar; ad -> `QShortcut` döndürür."""
    plot_target = window.dashboard
    created: dict[str, QShortcut] = {}
    for spec in SHORTCUTS:
        target = plot_target if spec.scope == "plot" else window
        shortcut = QShortcut(QKeySequence(spec.key), target)
        if spec.scope == "plot":
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        handler = getattr(window, spec.handler)
        shortcut.activated.connect(handler)
        created[spec.handler] = shortcut
    return created
