"""Paneller arası X ekseni senkronizasyonu — `F3-032`.

Bir gruba eklenen `PlotPanel`'ler ortak bir zaman penceresini paylaşır:
birinde pan/zoom yapınca ötekiler aynı X aralığına gelir. Döngü,
alıcı tarafın `apply_x_range()`'i (yayınlamadan uygulayan) ve
`PlotPanel._suppress_x_broadcast` bayrağıyla önlenir — kaynak panel
yeniden tetiklenmez.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from sonar_analyzer.ui.plots.plot_panel import PlotPanel


class XAxisLink:
    """`PlotPanel`'leri ortak X penceresinde bağlı tutan koordinatör."""

    def __init__(self) -> None:
        self._panels: list[PlotPanel] = []
        self._slots: dict[int, Callable[[float, float], None]] = {}

    @property
    def panels(self) -> tuple[PlotPanel, ...]:
        return tuple(self._panels)

    def add(self, panel: PlotPanel) -> None:
        """Paneli gruba katar; anında diğerlerinin X aralığına gelmez —
        ilk gezinmede senkron olur."""
        if panel in self._panels:
            return
        slot = partial(self._on_panel_x_changed, panel)
        self._slots[id(panel)] = slot
        panel.x_range_changed.connect(slot)
        self._panels.append(panel)

    def remove(self, panel: PlotPanel) -> None:
        """Paneli gruptan çıkarır; artık senkron olmaz."""
        if panel not in self._panels:
            return
        slot = self._slots.pop(id(panel), None)
        if slot is not None:
            panel.x_range_changed.disconnect(slot)
        self._panels.remove(panel)

    def _on_panel_x_changed(self, source: PlotPanel, x_min: float, x_max: float) -> None:
        for panel in self._panels:
            if panel is not source:
                panel.apply_x_range(x_min, x_max)
