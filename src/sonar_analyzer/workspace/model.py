"""Sürümlü workspace JSON modeli — `F3-067`.

Bir *workspace*, kullanıcının çalışma oturumunu yeniden kurmak için
gereken her şeydir: açık kayıt dosyaları, grafik panelleri (hangi
kanallar, hangi görünür aralık), genel görünüm tercihleri ve olay
filtresi. Bu modül yalnız **veri modelidir** — saf Python, Qt yok,
`GUI olmadan` doğrulanır. Dosyaya yazma / dock düzeni `F3-068`+.

Her belge bir ``schema_version`` taşır. Bilinmeyen (daha yeni) bir
sürüm `UnsupportedWorkspaceVersion` ile reddedilir; sürüm geçişi
`F3-071`'in işidir. Bozuk / eksik alan `WorkspaceError` verir —
sessizce varsayılana düşülmez.

Kabul: panel, kanal, görünüm ve filtre alanları serialize edilebilir
(round-trip: ``from_dict(to_dict(w)) == w``).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import cast

#: Bu kod tabanının yazdığı workspace şema sürümü.
WORKSPACE_SCHEMA_VERSION = 1

#: Grafik çalışma alanı yerleşimi (bkz. `ui/plots/plot_workspace.py`).
LAYOUT_MODES: tuple[str, ...] = ("tabs", "split")
#: İmleç zamanı gösterimi (bkz. `application/time_display.py`).
TIME_DISPLAY_MODES: tuple[str, ...] = ("elapsed", "utc", "local")
#: Yakınlaştırma kipi (bkz. `ui/plots/plot_panel.py`).
ZOOM_MODES: tuple[str, ...] = ("x", "y", "xy")


class WorkspaceError(ValueError):
    """Workspace belgesi bozuk, eksik ya da tip olarak geçersiz."""


class UnsupportedWorkspaceVersion(WorkspaceError):
    """Belgenin şema sürümü bu kod tabanınca okunamıyor."""


# -- tipli default_factory'ler (list[Unknown] uyarısını önler) ---


def _empty_str_list() -> list[str]:
    return []


def _empty_panel_list() -> list[PanelState]:
    return []


def _empty_group_list() -> list[list[int]]:
    return []


# -- yardımcı doğrulayıcılar -----------------------------------


def _as_dict(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{where}: nesne olmalı, {type(value).__name__} geldi")
    items = cast("dict[object, object]", value)
    return {str(key): val for key, val in items.items()}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _opt_pair(source: dict[str, object], key: str, where: str) -> tuple[float, float] | None:
    raw = source.get(key)
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        items = cast("Sequence[object]", raw)
        if len(items) == 2 and _is_number(items[0]) and _is_number(items[1]):
            return (float(cast("float", items[0])), float(cast("float", items[1])))
    raise WorkspaceError(f"{where}: '{key}' iki sayılı bir çift olmalı")


def _str_list(source: dict[str, object], key: str, where: str) -> list[str]:
    raw = source.get(key, [])
    if isinstance(raw, list):
        items = cast("list[object]", raw)
        if all(isinstance(v, str) for v in items):
            return [v for v in items if isinstance(v, str)]
    raise WorkspaceError(f"{where}: '{key}' metin listesi olmalı")


def _int_matrix(source: dict[str, object], key: str, where: str) -> list[list[int]]:
    raw = source.get(key, [])
    if isinstance(raw, list):
        groups: list[list[int]] = []
        for row in cast("list[object]", raw):
            if not isinstance(row, list) or not all(_is_int(v) for v in cast("list[object]", row)):
                raise WorkspaceError(f"{where}: '{key}' tam sayı listelerinden oluşmalı")
            groups.append([cast("int", v) for v in cast("list[object]", row)])
        return groups
    raise WorkspaceError(f"{where}: '{key}' liste olmalı")


def _one_of(value: str, allowed: tuple[str, ...], where: str, key: str) -> str:
    if value not in allowed:
        raise WorkspaceError(f"{where}: '{key}' {allowed} içinden olmalı, '{value}' geldi")
    return value


def _opt_str(source: dict[str, object], key: str, where: str) -> str | None:
    raw = source.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise WorkspaceError(f"{where}: '{key}' metin olmalı")
    return raw


def _opt_int(source: dict[str, object], key: str, where: str) -> int | None:
    raw = source.get(key)
    if raw is None:
        return None
    if not _is_int(raw):
        raise WorkspaceError(f"{where}: '{key}' tam sayı olmalı")
    return cast("int", raw)


# -- model -----------------------------------------------------


@dataclass(frozen=True)
class PanelState:
    """Tek bir grafik panelinin durumu — kanal(lar) ve görünür aralık."""

    channel_ids: list[str] = field(default_factory=_empty_str_list)
    x_range: tuple[float, float] | None = None
    y_range: tuple[float, float] | None = None
    zoom_mode: str = "xy"

    def __post_init__(self) -> None:
        _one_of(self.zoom_mode, ZOOM_MODES, "PanelState", "zoom_mode")

    def to_dict(self) -> dict[str, object]:
        return {
            "channel_ids": list(self.channel_ids),
            "x_range": list(self.x_range) if self.x_range is not None else None,
            "y_range": list(self.y_range) if self.y_range is not None else None,
            "zoom_mode": self.zoom_mode,
        }

    @classmethod
    def from_dict(cls, value: object) -> PanelState:
        data = _as_dict(value, "PanelState")
        return cls(
            channel_ids=_str_list(data, "channel_ids", "PanelState"),
            x_range=_opt_pair(data, "x_range", "PanelState"),
            y_range=_opt_pair(data, "y_range", "PanelState"),
            zoom_mode=_one_of(
                str(data.get("zoom_mode", "xy")), ZOOM_MODES, "PanelState", "zoom_mode"
            ),
        )


@dataclass(frozen=True)
class ViewState:
    """Panellerden bağımsız görünüm tercihleri."""

    time_display_mode: str = "elapsed"
    markers_visible: bool = True
    tx_visible: bool = True
    sync_x: bool = True

    def __post_init__(self) -> None:
        _one_of(self.time_display_mode, TIME_DISPLAY_MODES, "ViewState", "time_display_mode")

    def to_dict(self) -> dict[str, object]:
        return {
            "time_display_mode": self.time_display_mode,
            "markers_visible": self.markers_visible,
            "tx_visible": self.tx_visible,
            "sync_x": self.sync_x,
        }

    @classmethod
    def from_dict(cls, value: object) -> ViewState:
        data = _as_dict(value, "ViewState")
        return cls(
            time_display_mode=_one_of(
                str(data.get("time_display_mode", "elapsed")),
                TIME_DISPLAY_MODES,
                "ViewState",
                "time_display_mode",
            ),
            markers_visible=bool(data.get("markers_visible", True)),
            tx_visible=bool(data.get("tx_visible", True)),
            sync_x=bool(data.get("sync_x", True)),
        )


@dataclass(frozen=True)
class EventFilterState:
    """Events panelindeki birleşik filtrenin durumu."""

    source: str | None = None
    min_severity: str | None = None
    text: str = ""
    start_ns: int | None = None
    end_ns: int | None = None
    group_near: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "min_severity": self.min_severity,
            "text": self.text,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "group_near": self.group_near,
        }

    @classmethod
    def from_dict(cls, value: object) -> EventFilterState:
        data = _as_dict(value, "EventFilterState")
        return cls(
            source=_opt_str(data, "source", "EventFilterState"),
            min_severity=_opt_str(data, "min_severity", "EventFilterState"),
            text=str(data.get("text", "")),
            start_ns=_opt_int(data, "start_ns", "EventFilterState"),
            end_ns=_opt_int(data, "end_ns", "EventFilterState"),
            group_near=bool(data.get("group_near", False)),
        )


@dataclass(frozen=True)
class WorkspaceModel:
    """Bir çalışma oturumunun tamamı — sürümlü, JSON'a serileştirilebilir."""

    source_paths: list[str] = field(default_factory=_empty_str_list)
    panels: list[PanelState] = field(default_factory=_empty_panel_list)
    active_panel: int = 0
    layout_mode: str = "tabs"
    #: X-senkronlu panel indeksi kümeleri; ör. ``[[0, 1], [2, 3]]``.
    sync_groups: list[list[int]] = field(default_factory=_empty_group_list)
    #: Merkezde gösterilen görünüm sekmesi ("Time Series", "Transmission"…).
    active_view_tab: str = "Time Series"
    #: Qt `QMainWindow.saveState()` çıktısının base64'ü — dock yerleşimi.
    #: Opaktır; `F3-069` geri yüklerken uygular, model yorumlamaz.
    dock_state: str | None = None
    view: ViewState = field(default_factory=ViewState)
    event_filter: EventFilterState = field(default_factory=EventFilterState)
    schema_version: int = WORKSPACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _one_of(self.layout_mode, LAYOUT_MODES, "WorkspaceModel", "layout_mode")
        if self.panels and not 0 <= self.active_panel < len(self.panels):
            raise WorkspaceError(
                f"WorkspaceModel: active_panel {self.active_panel} panel aralığı dışında"
            )
        panel_count = len(self.panels)
        for group in self.sync_groups:
            for index in group:
                if not 0 <= index < panel_count:
                    raise WorkspaceError(
                        f"WorkspaceModel: sync_groups paneli {index} aralık dışında"
                    )

    # -- serileştirme -------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_paths": list(self.source_paths),
            "panels": [panel.to_dict() for panel in self.panels],
            "active_panel": self.active_panel,
            "layout_mode": self.layout_mode,
            "sync_groups": [list(group) for group in self.sync_groups],
            "active_view_tab": self.active_view_tab,
            "dock_state": self.dock_state,
            "view": self.view.to_dict(),
            "event_filter": self.event_filter.to_dict(),
        }

    def dumps(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, value: object) -> WorkspaceModel:
        data = _as_dict(value, "Workspace belgesi")
        version = data.get("schema_version")
        if not _is_int(version):
            raise WorkspaceError("Workspace belgesi 'schema_version' (tam sayı) taşımalı")
        assert isinstance(version, int)
        if version > WORKSPACE_SCHEMA_VERSION:
            raise UnsupportedWorkspaceVersion(
                f"Workspace şema sürümü {version} bu sürümce okunamıyor "
                f"(en yeni bilinen: {WORKSPACE_SCHEMA_VERSION})"
            )

        panels_raw = data.get("panels", [])
        if not isinstance(panels_raw, list):
            raise WorkspaceError("WorkspaceModel: 'panels' liste olmalı")

        active_panel = data.get("active_panel", 0)
        if not _is_int(active_panel):
            raise WorkspaceError("WorkspaceModel: 'active_panel' tam sayı olmalı")
        assert isinstance(active_panel, int)

        dock_state = data.get("dock_state")
        if dock_state is not None and not isinstance(dock_state, str):
            raise WorkspaceError("WorkspaceModel: 'dock_state' metin olmalı")

        return cls(
            source_paths=_str_list(data, "source_paths", "WorkspaceModel"),
            panels=[PanelState.from_dict(panel) for panel in cast("list[object]", panels_raw)],
            active_panel=active_panel,
            layout_mode=_one_of(
                str(data.get("layout_mode", "tabs")), LAYOUT_MODES, "WorkspaceModel", "layout_mode"
            ),
            sync_groups=_int_matrix(data, "sync_groups", "WorkspaceModel"),
            active_view_tab=str(data.get("active_view_tab", "Time Series")),
            dock_state=dock_state,
            view=ViewState.from_dict(data.get("view", {})),
            event_filter=EventFilterState.from_dict(data.get("event_filter", {})),
            schema_version=version,
        )

    @classmethod
    def loads(cls, text: str) -> WorkspaceModel:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise WorkspaceError(f"Workspace JSON çözümlenemedi: {exc}") from exc
        # Eski şema sürümleri önce güncel şekle taşınır — `F3-071`.
        from sonar_analyzer.workspace.migrate import migrate_document

        return cls.from_dict(migrate_document(data))

    def with_schema_version(self, version: int) -> WorkspaceModel:
        return replace(self, schema_version=version)
