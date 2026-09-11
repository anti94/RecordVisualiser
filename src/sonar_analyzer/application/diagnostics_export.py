"""Tanılama önizleme ve dışa aktarım — `F6-020`.

Kabul: **Kullanıcı içeriği görür; yalnız seçili öğeler pakete girer.**

`F6-019` neyin **girebileceğini** listeledi; bu modül neyin **girdiğine**
karar verir ve paketi yazar. İki kural taşır:

* **Önizleme, paketin kendisinden üretilir.** Kullanıcıya gösterilen
  liste ile yazılan arşiv ayrı hesaplanırsa er geç ayrışır ve kullanıcı
  gördüğünden başka bir şey göndermiş olur. Bu yüzden ikisi de aynı
  `Selection` nesnesinden çıkar.
* **Seçilmeyen hiçbir şey yazılmaz.** Arşive giren her dosya, seçimde
  karşılığı olduğu için girer; "zaten küçüktü, ben de ekledim" yoktur.

Arşiv `zip`'tir: Windows'ta ek araç istemeden açılır.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from sonar_analyzer.application.diagnostics import (
    DiagnosticItem,
    DiagnosticManifest,
    ItemCategory,
)

#: Arsiv icindeki ozet dosyasi. Paketin ne tasidigini ACAN kisi de gorur.
SUMMARY_NAME = "tanilama-ozeti.json"


@dataclass
class Selection:
    """Kullanıcının seçimi.

    Varsayılan seçim `F6-019`'un kuralıdır; kullanıcı bunu genişletebilir
    ya da daraltabilir, ama **her öğe açıkça** seçilir.
    """

    chosen: list[DiagnosticItem] = field(default_factory=lambda: [])

    @classmethod
    def from_defaults(cls, manifest: DiagnosticManifest) -> Selection:
        """Varsayılan seçimle başlar: ham veri **dışarıda**."""
        return cls(chosen=list(manifest.default_items))

    def add(self, item: DiagnosticItem) -> None:
        """Öğeyi seçime ekler (aynı öğe iki kez eklenmez)."""
        if item not in self.chosen:
            self.chosen.append(item)

    def remove(self, item: DiagnosticItem) -> None:
        if item in self.chosen:
            self.chosen.remove(item)

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.chosen)

    @property
    def includes_raw_data(self) -> bool:
        """Kullanıcı ham veriyi **açıkça** eklemiş mi?"""
        return any(item.category is ItemCategory.RAW_DATA for item in self.chosen)


@dataclass(frozen=True)
class PreviewLine:
    """Önizlemede gösterilen tek satır."""

    name: str
    category: str
    size_bytes: int
    warning: str = ""


def preview(selection: Selection) -> list[PreviewLine]:
    """Pakete **girecek** öğeleri satır satır gösterir.

    Önizleme seçimden üretilir; arşiv de aynı seçimden yazılır. Böylece
    kullanıcının gördüğü ile gönderdiği ayrışamaz.
    """
    lines: list[PreviewLine] = []
    for item in selection.chosen:
        warning = ""
        if item.category is ItemCategory.RAW_DATA:
            warning = "HAM SENSOR VERISI — bu dosya olcum verinizi icerir."
        elif item.category is ItemCategory.WORKSPACE:
            warning = "Calisma alani; analiz zinciri ve isaretlerinizi icerir."
        lines.append(
            PreviewLine(
                name=item.name,
                category=item.category.value,
                size_bytes=item.size_bytes,
                warning=warning,
            )
        )
    return lines


@dataclass
class ExportResult:
    """Yazılan paketin kaydı."""

    path: Path
    written_names: list[str] = field(default_factory=lambda: [])
    total_bytes: int = 0

    @property
    def ok(self) -> bool:
        return self.path.is_file() and bool(self.written_names)


def export(
    selection: Selection,
    target: Path,
    *,
    session_id: str = "",
    app_version: str = "",
) -> ExportResult:
    """Seçili öğeleri bir `zip` arşivine yazar.

    Seçimde olmayan hiçbir şey yazılmaz. Dosyası olmayan öğeler (oturum,
    sürüm) özet dosyasında metin olarak yer alır; onlar için ayrıca bir
    dosya okunmaz.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    summary = {
        "session_id": session_id,
        "app_version": app_version,
        "items": [
            {
                "name": item.name,
                "category": item.category.value,
                "size_bytes": item.size_bytes,
                "detail": item.detail,
            }
            for item in selection.chosen
        ],
        "includes_raw_data": selection.includes_raw_data,
    }

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(SUMMARY_NAME, json.dumps(summary, indent=2, ensure_ascii=False))
        written.append(SUMMARY_NAME)

        for item in selection.chosen:
            if item.path is None or not item.path.is_file():
                continue
            # Arsiv icinde kategoriye gore ayrilir; acan kisi neyin ne
            # oldugunu klasor adindan gorur.
            arcname = f"{item.category.value}/{item.name}"
            archive.write(item.path, arcname)
            written.append(arcname)

    return ExportResult(
        path=target,
        written_names=written,
        total_bytes=target.stat().st_size if target.is_file() else 0,
    )
