"""Dışa aktarma hedefi ve üzerine yazma kararı — `F3-065`.

Saf Python: Qt yok, `GUI olmadan` doğrulanır. GUI dosya/onay
diyaloglarını enjekte eder; bu modül yalnız **kararı** verir:

* İstenen biçime göre doğru uzantıyı garanti eder (`ensure_extension`).
* Hedef dosya varsa ve kullanıcı onaylamadıysa dışa aktarmayı iptal
  eder — var olan dosya **dokunulmaz** (`resolve_target` -> ``None``).
* Ham (kalibrasyonsuz) / işlenmiş (ölçekli) veri seçimini açık bir
  numaralandırma olarak taşır (`DataVariant`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ExportKind(str, Enum):
    """Uygulanmış dışa aktarma biçimleri."""

    PNG = "png"
    SVG = "svg"
    CSV = "csv"


class DataVariant(str, Enum):
    """CSV'de yazılacak değerler ham mı, işlenmiş (ölçekli) mi."""

    PROCESSED = "processed"
    RAW = "raw"


#: Kart etiketinden `ExportKind`'e — yalnız uygulanmış biçimler.
FORMAT_TO_KIND: dict[str, ExportKind] = {
    "PNG": ExportKind.PNG,
    "SVG": ExportKind.SVG,
    "CSV": ExportKind.CSV,
}

#: Her biçimin zorunlu dosya uzantısı.
KIND_EXTENSION: dict[ExportKind, str] = {
    ExportKind.PNG: ".png",
    ExportKind.SVG: ".svg",
    ExportKind.CSV: ".csv",
}

#: Qt kaydetme diyaloğu için ad filtresi.
KIND_FILE_FILTER: dict[ExportKind, str] = {
    ExportKind.PNG: "PNG görüntü (*.png)",
    ExportKind.SVG: "SVG çizim (*.svg)",
    ExportKind.CSV: "CSV veri (*.csv)",
}

#: `exists(path) -> bool` — dosya sisteminden bağımsız test edilebilsin diye.
FileExists = Callable[[Path], bool]
#: `confirm_overwrite(path) -> bool` — kullanıcı üzerine yazmayı onaylıyor mu.
ConfirmOverwrite = Callable[[Path], bool]


@dataclass(frozen=True)
class ExportPlan:
    """Çözülmüş bir dışa aktarma isteği — dispatch için hazır."""

    kind: ExportKind
    path: Path
    variant: DataVariant = DataVariant.PROCESSED
    selected_range_only: bool = False
    include_metadata: bool = True

    @property
    def is_image(self) -> bool:
        return self.kind in (ExportKind.PNG, ExportKind.SVG)

    @property
    def wants_raw(self) -> bool:
        return self.variant is DataVariant.RAW


def kind_for_format(format_label: str) -> ExportKind:
    """Kart etiketini (`"CSV"`) `ExportKind`'e çevirir.

    Henüz uygulanmamış bir biçim (`"TSV"`, `"JSON"`) için `KeyError`.
    """
    try:
        return FORMAT_TO_KIND[format_label.upper()]
    except KeyError as exc:
        raise KeyError(f"Desteklenmeyen dışa aktarma biçimi: {format_label}") from exc


def ensure_extension(path: Path, kind: ExportKind) -> Path:
    """`path`'in `kind`'e uygun uzantıyla bitmesini sağlar (yoksa ekler)."""
    wanted = KIND_EXTENSION[kind]
    if path.suffix.lower() == wanted:
        return path
    return path.with_name(path.name + wanted)


def resolve_target(
    path: str | Path,
    kind: ExportKind,
    *,
    exists: FileExists,
    confirm_overwrite: ConfirmOverwrite,
) -> Path | None:
    """Yazılacak nihai yolu döndürür; kullanıcı üzerine yazmayı reddederse ``None``.

    ``None`` döndüğünde çağıran **hiçbir şey yazmamalıdır** — var olan
    dosya olduğu gibi kalır.
    """
    dest = ensure_extension(Path(path), kind)
    if exists(dest) and not confirm_overwrite(dest):
        return None
    return dest
