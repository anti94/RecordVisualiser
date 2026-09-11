"""Tanılama paketi içeriği — `F6-019`.

Kabul: **Session, sürüm ve hata logları listelenir; ham sensör veri
varsayılan değildir.**

Bir tanılama paketi, kullanıcıdan "şunu gönderir misin" diye istenen
şeydir; ne taşıdığı bu yüzden **kullanıcının kararı** olmalıdır. Modül bu
kararı iki katmanla korur:

* her öğe bir **kategori** taşır ve `default_selected` bayrağıyla gelir,
* **ham sensör verisi hiçbir zaman varsayılan olarak seçili değildir**.
  Kayıtlar kullanıcının asıl verisidir; bir hata raporuna farkında
  olmadan eklenmesi, ölçüm verisinin dışarı çıkması demektir.

Liste üretmek dosya **okumaz**: yalnız neyin var olduğunu ve ne kadar yer
tuttuğunu bildirir. İçeriğin okunması ve paketlenmesi `F6-020`'nin işidir
ve orada da yalnız **seçili** öğeler okunur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

#: Tek bir dosyanin listeye girerken taranacagi ust sinir yoktur; ancak
#: cok sayida log birikmis olabilir, bu yuzden en yeniler alinir.
MAX_LOG_FILES = 20


class ItemCategory(str, Enum):
    """Tanılama öğesinin türü."""

    SESSION = "session"
    VERSION = "surum"
    ERROR_LOG = "hata_logu"
    SETTINGS = "ayarlar"
    WORKSPACE = "workspace"
    RAW_DATA = "ham_veri"


#: Varsayilan olarak SECILI gelen kategoriler. `RAW_DATA` bilerek
#: listede yoktur: kullanicinin olcum verisi, istemeden gonderilmemeli.
DEFAULT_SELECTED: frozenset[ItemCategory] = frozenset(
    {
        ItemCategory.SESSION,
        ItemCategory.VERSION,
        ItemCategory.ERROR_LOG,
        ItemCategory.SETTINGS,
    }
)


@dataclass(frozen=True)
class DiagnosticItem:
    """Tanılama paketine girebilecek tek bir öğe."""

    name: str
    category: ItemCategory
    size_bytes: int = 0
    path: Path | None = None
    detail: str = ""

    @property
    def default_selected(self) -> bool:
        """Varsayılan olarak seçili mi?

        Ham veri hiçbir koşulda varsayılan değildir; bu bir kural, bir
        tercih değil.
        """
        return self.category in DEFAULT_SELECTED


@dataclass
class DiagnosticManifest:
    """Tanılama paketinin içerik listesi."""

    items: list[DiagnosticItem] = field(default_factory=lambda: [])

    @property
    def default_items(self) -> list[DiagnosticItem]:
        return [item for item in self.items if item.default_selected]

    @property
    def optional_items(self) -> list[DiagnosticItem]:
        return [item for item in self.items if not item.default_selected]

    @property
    def default_bytes(self) -> int:
        return sum(item.size_bytes for item in self.default_items)

    def by_category(self, category: ItemCategory) -> list[DiagnosticItem]:
        return [item for item in self.items if item.category is category]


def _size_of(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def build_manifest(
    *,
    session_id: str,
    app_version: str,
    log_dir: Path | None = None,
    settings_path: Path | None = None,
    workspace_path: Path | None = None,
    recording_paths: list[Path] | None = None,
) -> DiagnosticManifest:
    """Tanılama paketine girebilecek öğeleri listeler.

    Hiçbir dosya **okunmaz**; yalnız varlığı ve boyutu bildirilir.
    """
    manifest = DiagnosticManifest()

    manifest.items.append(
        DiagnosticItem(
            name=f"oturum-{session_id}",
            category=ItemCategory.SESSION,
            detail="Oturum kimligi; log satirlariyla eslestirmek icin.",
        )
    )
    manifest.items.append(
        DiagnosticItem(
            name=f"surum-{app_version}",
            category=ItemCategory.VERSION,
            detail="Uygulama surumu ve calisma ortami.",
        )
    )

    if log_dir is not None and log_dir.is_dir():
        logs = sorted(
            (path for path in log_dir.glob("*.log") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:MAX_LOG_FILES]
        for path in logs:
            manifest.items.append(
                DiagnosticItem(
                    name=path.name,
                    category=ItemCategory.ERROR_LOG,
                    size_bytes=_size_of(path),
                    path=path,
                    detail="Uygulama logu.",
                )
            )

    if settings_path is not None and settings_path.is_file():
        manifest.items.append(
            DiagnosticItem(
                name=settings_path.name,
                category=ItemCategory.SETTINGS,
                size_bytes=_size_of(settings_path),
                path=settings_path,
                detail="Uygulama ayarlari.",
            )
        )

    if workspace_path is not None and workspace_path.is_file():
        manifest.items.append(
            DiagnosticItem(
                name=workspace_path.name,
                category=ItemCategory.WORKSPACE,
                size_bytes=_size_of(workspace_path),
                path=workspace_path,
                detail="Calisma alani; analiz zinciri ve isaretler. Varsayilan DEGIL.",
            )
        )

    for path in recording_paths or []:
        if not path.is_file():
            continue
        manifest.items.append(
            DiagnosticItem(
                name=path.name,
                category=ItemCategory.RAW_DATA,
                size_bytes=_size_of(path),
                path=path,
                detail="HAM SENSOR VERISI. Varsayilan DEGIL; yalniz acikca secilirse eklenir.",
            )
        )

    return manifest
