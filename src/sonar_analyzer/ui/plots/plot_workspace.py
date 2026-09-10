"""Çoklu grafik çalışma alanı: tab + bölünmüş görünüm — `F3-033`.

Birden fazla `PlotPanel`'i bir arada tutar; paneller **açılır, bölünür
ve bağımsız kapatılır**. Tüm paneller ortak bir `XAxisLink`'e (`F3-032`)
bağlanır, böylece birinde gezinme ötekileri günceller.

Yerleşim iki kipten biridir:

* ``"tabs"`` — her panel bir sekmede (öntanımlı),
* ``"split"`` — paneller yan yana (`QSplitter`).

Kip değişince var olan paneller yeni kaba **taşınır** (yeniden
oluşturulmaz), bağlantıları ve durumları korunur.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QTabWidget, QVBoxLayout, QWidget

from sonar_analyzer.ui.plots.plot_panel import PlotPanel
from sonar_analyzer.ui.plots.x_axis_link import XAxisLink

WORKSPACE_LAYOUTS: tuple[str, ...] = ("tabs", "split")
DEFAULT_LAYOUT = "tabs"


class PlotWorkspace(QWidget):
    """Tab/bölünmüş yerleşimde birden çok `PlotPanel` barındıran alan."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plot_workspace")
        self._panels: list[PlotPanel] = []
        self._titles: dict[int, str] = {}
        self._link = XAxisLink()
        self._layout_mode = DEFAULT_LAYOUT

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._container: QWidget = self._build_container(DEFAULT_LAYOUT)
        self._outer.addWidget(self._container)

    # -- sorgular ----------------------------------------------------

    @property
    def count(self) -> int:
        return len(self._panels)

    @property
    def layout_mode(self) -> str:
        return self._layout_mode

    @property
    def is_tab_layout(self) -> bool:
        return isinstance(self._container, QTabWidget)

    @property
    def is_split_layout(self) -> bool:
        return isinstance(self._container, QSplitter)

    def index_of(self, panel: PlotPanel) -> int:
        """Panelin çalışma alanındaki sırası; yoksa `-1`."""
        return self._panels.index(panel) if panel in self._panels else -1

    @property
    def panels(self) -> tuple[PlotPanel, ...]:
        return tuple(self._panels)

    def panel_at(self, index: int) -> PlotPanel:
        return self._panels[index]

    @property
    def active_panel(self) -> PlotPanel | None:
        """Tab kipinde seçili sekme; bölünmüşte ilk panel; hiç yoksa `None`."""
        if not self._panels:
            return None
        if isinstance(self._container, QTabWidget):
            current = self._container.currentWidget()
            if isinstance(current, PlotPanel):
                return current
        return self._panels[0]

    # -- panel yasam dongusu --------------------------------------

    def open_panel(self, title: str | None = None) -> PlotPanel:
        """Yeni bir `PlotPanel` açar, ortak X bağlantısına katar ve döndürür."""
        panel = PlotPanel(self)
        name = title or f"Grafik {len(self._panels) + 1}"
        self._titles[id(panel)] = name
        self._panels.append(panel)
        self._link.add(panel)
        self._attach(panel, name)
        return panel

    def close_panel(self, panel: PlotPanel) -> None:
        """Bir paneli kapatır — diğerleri etkilenmez (bağımsız kapatma)."""
        if panel not in self._panels:
            return
        self._link.remove(panel)
        self._detach(panel)
        self._panels.remove(panel)
        self._titles.pop(id(panel), None)
        panel.setParent(None)
        panel.deleteLater()

    def close_panel_at(self, index: int) -> None:
        """Sıra numarasına göre kapatır — sekme kapatma düğmesinin yolu."""
        if 0 <= index < len(self._panels):
            self.close_panel(self._panels[index])

    def close_all(self) -> None:
        for panel in list(self._panels):
            self.close_panel(panel)

    # -- yerlesim kipi -------------------------------------------

    def set_layout_mode(self, mode: str) -> None:
        """Yerleşimi ``"tabs"`` / ``"split"`` arasında değiştirir; panelleri taşır."""
        if mode not in WORKSPACE_LAYOUTS:
            raise ValueError(f"Bilinmeyen yerlesim: {mode!r}")
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        new_container = self._build_container(mode)
        for panel in self._panels:
            panel.setParent(None)
            self._add_to_container(new_container, panel, self._titles.get(id(panel), ""))
        self._outer.removeWidget(self._container)
        self._container.setParent(None)
        self._container.deleteLater()
        self._container = new_container
        self._outer.addWidget(self._container)

    def split(self) -> None:
        self.set_layout_mode("split")

    def tabs(self) -> None:
        self.set_layout_mode("tabs")

    # -- ic yardimcilar ----------------------------------------

    def _build_container(self, mode: str) -> QWidget:
        if mode == "split":
            splitter = QSplitter(Qt.Orientation.Horizontal, self)
            splitter.setObjectName("plot_workspace_split")
            return splitter
        tabs = QTabWidget(self)
        tabs.setObjectName("plot_workspace_tabs")
        tabs.setTabsClosable(True)
        tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        return tabs

    def _attach(self, panel: PlotPanel, title: str) -> None:
        self._add_to_container(self._container, panel, title)

    def _detach(self, panel: PlotPanel) -> None:
        container = self._container
        if isinstance(container, QTabWidget):
            index = container.indexOf(panel)
            if index != -1:
                container.removeTab(index)
        else:
            panel.setParent(None)

    @staticmethod
    def _add_to_container(container: QWidget, panel: PlotPanel, title: str) -> None:
        if isinstance(container, QTabWidget):
            container.addTab(panel, title)
        elif isinstance(container, QSplitter):
            container.addWidget(panel)

    def _on_tab_close_requested(self, index: int) -> None:
        container = self._container
        if isinstance(container, QTabWidget):
            widget = container.widget(index)
            if isinstance(widget, PlotPanel):
                self.close_panel(widget)

    # `_on_tab_close_requested` içi test edilebilsin diye ayrı bir
    # sıra-tabanlı yol da var: `close_panel_at`.
