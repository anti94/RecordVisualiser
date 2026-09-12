"""Klasör seviyesinde indeks — `F7-031`…`F7-035`.

10 dakikalık bir kayıt 1.200 dosya taşır. Her birini açıp taramak, dosya
başına yalnız 1 ms sürse bile 1,2 saniye eder ve ilk açılış bütçesinin
tamamını yer (`docs/format/profile-c.md` §3.4). Bu yüzden klasör bir kez
taranır ve sonuç tek bir dosyada saklanır.

İndeks **türetilmiş veridir**: silinirse yeniden kurulur, hiçbir bilgi
kaybolmaz. Bu yüzden geçersizleşmesi ucuz olmalı ve şüphe hâlinde
yeniden kurmak, eski bir indeksi kullanmaya yeğlenir.

Parmak izi her dosyanın hash'iyle değil, **adı, boyutu ve değişiklik
zamanıyla** hesaplanır. 1,17 GiB'i hash'lemek indeksin kendisinden uzun
sürerdi; amaç kriptografik güvence değil, "bu klasör değişti mi"
sorusuna ucuz cevap vermektir.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sonar_analyzer.io.decoders.profile_c_folder import (
    INDEX_DIRNAME,
    RecordingFolder,
    Stream,
    StreamFile,
)

#: Indeks bicim surumu. Bicim degisince eski indeksler gecersizlesir.
INDEX_FORMAT_VERSION = 1

INDEX_FILENAME = "folder-index.json"


@dataclass(frozen=True)
class FileEntry:
    """İndekste bir dosyanın kaydı."""

    counter: int
    name: str
    size_bytes: int
    frame_count: int
    #: Ilk ve son frame'in zaman damgasi. Cozulmediyse None.
    start_ns: int | None = None
    end_ns: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "counter": self.counter,
            "name": self.name,
            "size_bytes": self.size_bytes,
            "frame_count": self.frame_count,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> FileEntry:
        return cls(
            counter=int(raw["counter"]),
            name=str(raw["name"]),
            size_bytes=int(raw["size_bytes"]),
            frame_count=int(raw["frame_count"]),
            start_ns=None if raw.get("start_ns") is None else int(raw["start_ns"]),
            end_ns=None if raw.get("end_ns") is None else int(raw["end_ns"]),
        )


@dataclass(frozen=True)
class FolderIndex:
    """Bir kayıt klasörünün indeksi."""

    fingerprint: str
    schema_fingerprint: str
    entries: dict[str, tuple[FileEntry, ...]]
    format_version: int = INDEX_FORMAT_VERSION

    @property
    def file_count(self) -> int:
        return sum(len(items) for items in self.entries.values())

    @property
    def frame_count(self) -> int:
        return sum(entry.frame_count for items in self.entries.values() for entry in items)

    def stream(self, stream: Stream) -> tuple[FileEntry, ...]:
        return self.entries.get(stream.value, ())

    @property
    def time_range_ns(self) -> tuple[int, int] | None:
        """Bütün akımları kapsayan zaman aralığı; hiç damga yoksa `None`."""
        starts = [
            entry.start_ns
            for items in self.entries.values()
            for entry in items
            if entry.start_ns is not None
        ]
        ends = [
            entry.end_ns
            for items in self.entries.values()
            for entry in items
            if entry.end_ns is not None
        ]
        if not starts or not ends:
            return None
        return min(starts), max(ends)

    def as_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "fingerprint": self.fingerprint,
            "schema_fingerprint": self.schema_fingerprint,
            "entries": {
                name: [entry.as_dict() for entry in items] for name, items in self.entries.items()
            },
        }


def _stat_signature(entry: StreamFile) -> str:
    """Bir dosyanın ucuz imzası: ad, boyut, değişiklik zamanı."""
    info = entry.path.stat()
    return f"{entry.path.name}:{info.st_size}:{info.st_mtime_ns}"


def folder_fingerprint(folder: RecordingFolder) -> str:
    """Klasörün parmak izi — `F7-032`.

    Her dosyanın **içeriği** değil, adı, boyutu ve değişiklik zamanı
    özetlenir. 1,17 GiB'i hash'lemek indeksin kendisinden uzun sürerdi ve
    amaç kriptografik güvence değil; sorulan şey "bu klasör değişti mi".

    Bir dosya eklenir, silinir, büyür ya da yeniden yazılırsa parmak izi
    değişir ve indeks yeniden kurulur.
    """
    parts: list[str] = [f"format={INDEX_FORMAT_VERSION}"]
    for stream in Stream:
        listing = folder.listing(stream)
        parts.append(f"stream={stream.value}:{len(listing.files)}")
        parts.extend(_stat_signature(entry) for entry in listing.files)
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def index_path(folder: RecordingFolder) -> Path:
    """İndeksin yazılacağı yol."""
    return folder.path / INDEX_DIRNAME / INDEX_FILENAME


def write_index(folder: RecordingFolder, index: FolderIndex) -> Path | None:
    """İndeksi atomik olarak yazar — `F7-033`.

    Geçici bir dosyaya yazılıp yerine taşınır. Yarıda kesilen bir yazım
    **geçersiz bir indeks bırakmaz**: yarım bir JSON, sonraki açılışta
    ayrıştırma hatası verir ve o hata veriyi okumayı engellerdi.

    Klasör salt okunursa `None` döner ve kayıt yine açılır (`F7-034`).
    Kayıt klasörünü yazılabilir olmaya zorlamak, arşivdeki bir kaydı
    incelemeyi imkânsız kılardı.
    """
    target = index_path(folder)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(index.as_dict(), ensure_ascii=False, indent=1), encoding="utf-8"
        )
        os.replace(temporary, target)
    except OSError:
        return None
    return target


def read_index(folder: RecordingFolder) -> FolderIndex | None:
    """İndeksi okur; yoksa, bozuksa ya da eskiyse `None`.

    Şüphe hâlinde `None` dönmek bilinçlidir. İndeks türetilmiş veridir;
    yeniden kurmanın bedeli birkaç saniyedir. Bozuk bir indeksi kurtarmaya
    çalışmak, yanlış zaman aralıklarıyla çalışmak demektir.
    """
    path = index_path(folder)
    if not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None

    # json.loads `Any` dondurur; ham `Any` degerler donguye girince kati
    # tip denetiminde bilinmeyen tiplere yol acar. Daraltma burada bir kez
    # yapilir ve asagisi tam tipli calisir.
    raw = cast("dict[str, Any]", parsed)
    if raw.get("format_version") != INDEX_FORMAT_VERSION:
        return None

    try:
        raw_entries = raw["entries"]
        if not isinstance(raw_entries, dict):
            return None
        entries: dict[str, tuple[FileEntry, ...]] = {}
        for name, items in cast("dict[str, Any]", raw_entries).items():
            if not isinstance(items, list):
                return None
            entries[str(name)] = tuple(
                FileEntry.from_dict(cast("dict[str, Any]", item))
                for item in cast("list[Any]", items)
            )
        return FolderIndex(
            fingerprint=str(raw["fingerprint"]),
            schema_fingerprint=str(raw["schema_fingerprint"]),
            entries=entries,
            format_version=int(raw["format_version"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def is_current(index: FolderIndex, folder: RecordingFolder, schema_fingerprint: str) -> bool:
    """İndeks bu klasör ve bu şema için hâlâ geçerli mi — `F7-032`.

    İki parmak izi ayrı tutulur. Klasör değişmeden şema değişebilir: aynı
    dosyalar farklı bir yerleşimle okunur ve indeksteki frame sayıları
    yanlış olur. Tek bir parmak iziyle bu ayrım kaybolurdu.
    """
    return (
        index.format_version == INDEX_FORMAT_VERSION
        and index.fingerprint == folder_fingerprint(folder)
        and index.schema_fingerprint == schema_fingerprint
    )
