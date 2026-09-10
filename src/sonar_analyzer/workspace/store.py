"""Workspace dosyasını yaz / oku — `F3-068`, `F3-069`.

Saf dosya G/Ç: model `workspace/model.py`'de, GUI'siz doğrulanır.
Yazma **atomiktir** (`<hedef>.part` -> `os.replace`), böylece yarıda
kesilen bir kayıt eski workspace'i bozmaz.
"""

from __future__ import annotations

import os
from pathlib import Path

from sonar_analyzer.workspace.model import WorkspaceModel

#: Workspace dosyası için önerilen uzantı.
WORKSPACE_SUFFIX = ".sonar-workspace.json"


def save_workspace(model: WorkspaceModel, path: str | Path) -> Path:
    """`model`'i `path`'e JSON olarak **atomik** yazar; yazılan yolu döndürür."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    try:
        partial.write_text(model.dumps(), encoding="utf-8")
        os.replace(partial, dest)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return dest


def load_workspace(path: str | Path) -> WorkspaceModel:
    """`path`'teki workspace belgesini okur ve doğrular.

    `FileNotFoundError` — dosya yok. `WorkspaceError` — belge bozuk ya da
    şema sürümü okunamıyor.
    """
    return WorkspaceModel.loads(Path(path).read_text(encoding="utf-8"))
