"""Workspace şema sürüm geçişleri — `F3-071`.

Bir workspace belgesi diskte kaldığı sürece eski bir şema sürümüyle
yazılmış olabilir. Bu modül belgeyi **adım adım** güncel sürüme taşır
(`v0 -> v1 -> ...`), böylece `WorkspaceModel.from_dict` her zaman güncel
şekli görür.

* Eski, bilinen bir sürüm: sırayla dönüştürülür.
* Güncel sürüm: dokunulmaz.
* Bilinmeyen **daha yeni** bir sürüm: `UnsupportedWorkspaceVersion` ile
  anlaşılır biçimde reddedilir (kullanıcıya "uygulamayı güncelleyin"
  denir), sessiz veri kaybı olmaz.

Saf Python: `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from sonar_analyzer.workspace.model import (
    WORKSPACE_SCHEMA_VERSION,
    UnsupportedWorkspaceVersion,
    WorkspaceError,
)

#: Bu kod tabanının okuyabildiği en eski şema sürümü.
OLDEST_SUPPORTED_VERSION = 0


def _migrate_0_to_1(doc: dict[str, object]) -> dict[str, object]:
    """Legacy (v0) şeklini v1'e taşır.

    v0 farkları:
    * ``open_files``            -> ``source_paths``
    * ``tab``                   -> ``active_view_tab``
    * panel ``channels``        -> panel ``channel_ids``
    * ``sync_groups`` / ``dock_state`` / ``view`` / ``event_filter`` yok
      (v1 varsayılanlarına bırakılır).
    """
    panels_in = doc.get("panels", [])
    panels_out: list[dict[str, object]] = []
    if isinstance(panels_in, list):
        for raw in cast("list[object]", panels_in):
            panel: dict[str, object] = (
                {str(k): v for k, v in cast("dict[object, object]", raw).items()}
                if isinstance(raw, dict)
                else {}
            )
            panels_out.append(
                {
                    "channel_ids": panel.get("channels", panel.get("channel_ids", [])),
                    "x_range": panel.get("x_range"),
                    "y_range": panel.get("y_range"),
                    "zoom_mode": panel.get("zoom_mode", "xy"),
                }
            )

    migrated: dict[str, object] = {
        "schema_version": 1,
        "source_paths": doc.get("open_files", doc.get("source_paths", [])),
        "panels": panels_out,
        "active_panel": doc.get("active_panel", 0),
        "layout_mode": doc.get("layout_mode", "tabs"),
        "active_view_tab": doc.get("tab", doc.get("active_view_tab", "Time Series")),
    }
    return migrated


def _migrate_1_to_2(doc: dict[str, object]) -> dict[str, object]:
    """v1'i v2'ye taşır — `F4-076`.

    v2 üç alan ekler: `derived_channels` (türetilmiş kanal tanımları),
    `annotations` (bookmark/annotation) ve `series_styles` (kanal renkleri).
    v1 belgelerinde hiçbiri yoktur; boş varsayılanlarla doldurulur.
    **Hiçbir v1 alanı değişmez veya silinmez**, yalnız eklenir.
    """
    migrated = dict(doc)
    migrated["schema_version"] = 2
    migrated.setdefault("derived_channels", [])
    migrated.setdefault("annotations", [])
    migrated.setdefault("series_styles", {})
    return migrated


def _migrate_2_to_3(doc: dict[str, object]) -> dict[str, object]:
    """v2'yi v3'e taşır — `F4-077`.

    v3 tek alan ekler: `processing_chain` (Custom sekmesindeki işlem
    zinciri). v2 belgelerinde yoktur; boş listeyle doldurulur. Başka
    hiçbir alan değişmez.
    """
    migrated = dict(doc)
    migrated["schema_version"] = 3
    migrated.setdefault("processing_chain", [])
    return migrated


#: `v -> (v+1)` dönüştürücüleri. Her adım `schema_version`'ı da yükseltir.
_MIGRATIONS: dict[int, Callable[[dict[str, object]], dict[str, object]]] = {
    0: _migrate_0_to_1,
    1: _migrate_1_to_2,
    2: _migrate_2_to_3,
}


def _document_version(doc: dict[str, object]) -> int:
    version = doc.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise WorkspaceError("Workspace belgesi 'schema_version' (tam sayı) taşımalı")
    return version


def migrate_document(raw: object) -> dict[str, object]:
    """`raw` workspace belgesini güncel şema sürümüne taşır ve döndürür.

    * `WorkspaceError` — belge nesne değil ya da 'schema_version' yok.
    * `UnsupportedWorkspaceVersion` — sürüm bu kod tabanından yeni.
    """
    if not isinstance(raw, dict):
        raise WorkspaceError(f"Workspace belgesi bir nesne olmalı, {type(raw).__name__} geldi")
    doc = {str(key): value for key, value in cast("dict[object, object]", raw).items()}

    version = _document_version(doc)
    if version > WORKSPACE_SCHEMA_VERSION:
        raise UnsupportedWorkspaceVersion(
            f"Bu workspace şema sürümü {version} ile yazılmış; bu uygulama en çok "
            f"sürüm {WORKSPACE_SCHEMA_VERSION}'i okuyabilir. Uygulamayı güncelleyin."
        )
    if version < OLDEST_SUPPORTED_VERSION:
        raise UnsupportedWorkspaceVersion(
            f"Workspace şema sürümü {version} çok eski; en eski desteklenen "
            f"sürüm {OLDEST_SUPPORTED_VERSION}."
        )

    while version < WORKSPACE_SCHEMA_VERSION:
        step = _MIGRATIONS.get(version)
        if step is None:  # pragma: no cover - kayıtlı adımlar süreklidir
            raise WorkspaceError(f"Workspace sürüm {version} için geçiş adımı tanımlı değil")
        doc = step(doc)
        version = _document_version(doc)

    return doc
