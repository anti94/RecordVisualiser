"""Son geçerli workspace kurtarması — `F6-021`.

Kabul: **Kesinti sonrası sağlam oturum önerilir; bozuk dosya etkin
oturumu ezmez.**

Uygulama beklenmedik biçimde kapandığında (çökme, elektrik kesintisi)
kullanıcının açık oturumu kaybolur. Bu modül düzenli aralıklarla
**kontrol noktası** yazar ve açılışta kurtarılabilir bir oturum önerir.

İki kural taşır ve ikisi de kabul kriterinin karşılığıdır:

* **Önerilen oturum sağlamdır.** Bir kontrol noktası ancak gerçekten
  **yüklenebiliyorsa** önerilir; dosyanın var olması yetmez. Bu yüzden
  aday, önerilmeden önce okunup doğrulanır.
* **Bozuk dosya hiçbir şeyi ezmez.** Kurtarma bir **öneridir**; kullanıcı
  kabul edene kadar etkin oturuma dokunulmaz. En yeni kontrol noktası
  bozuksa bir önceki sağlam olan önerilir, hiçbiri sağlam değilse
  **öneri yapılmaz** — yarım bir oturumla açmak, hiç açmamaktan kötüdür.

Kontrol noktaları sayıca sınırlıdır; eskiler silinir, yoksa oturum
dizini sınırsız büyür.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sonar_analyzer.workspace.model import WorkspaceError, WorkspaceModel
from sonar_analyzer.workspace.store import load_workspace, save_workspace

#: Kontrol noktasi dosya adi oneki.
CHECKPOINT_PREFIX = "autosave-"
CHECKPOINT_SUFFIX = ".json"

#: Saklanan kontrol noktasi sayisi. Birden fazla tutulur ki en yenisi
#: bozuk cikarsa bir onceki sagam olan onerilebilsin.
MAX_CHECKPOINTS = 5


@dataclass(frozen=True)
class RecoveryCandidate:
    """Kurtarılabilir bir oturum önerisi."""

    path: Path
    model: WorkspaceModel
    saved_at: datetime

    @property
    def age_seconds(self) -> float:
        return max(0.0, (datetime.now(timezone.utc) - self.saved_at).total_seconds())


def checkpoint_dir(root: Path) -> Path:
    """Kontrol noktalarının tutulduğu dizin."""
    return root / "recovery"


def write_checkpoint(model: WorkspaceModel, root: Path) -> Path:
    """Bir kontrol noktası yazar ve eskileri budar.

    Yazma `save_workspace`'in atomik yoluna devredilir: yarıda kesilen
    bir yazım, önceki kontrol noktalarını bozmaz.
    """
    directory = checkpoint_dir(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = directory / f"{CHECKPOINT_PREFIX}{stamp}{CHECKPOINT_SUFFIX}"
    saved = save_workspace(model, target)
    _prune(directory)
    return saved


def list_checkpoints(root: Path) -> list[Path]:
    """Kontrol noktaları, **en yeni önce**."""
    directory = checkpoint_dir(root)
    if not directory.is_dir():
        return []
    found = [
        path
        for path in directory.glob(f"{CHECKPOINT_PREFIX}*{CHECKPOINT_SUFFIX}")
        if path.is_file()
    ]
    return sorted(found, key=lambda path: path.name, reverse=True)


def find_recoverable(root: Path) -> RecoveryCandidate | None:
    """En yeni **sağlam** kontrol noktasını döner; yoksa `None`.

    Adaylar en yeniden eskiye denenir ve her biri gerçekten **okunur**.
    Bozuk olan atlanır; okunabilen ilk aday önerilir. Hiçbiri okunamazsa
    öneri yapılmaz — yarım bir oturum açmak, hiç açmamaktan kötüdür.
    """
    for path in list_checkpoints(root):
        try:
            model = load_workspace(path)
        except (OSError, WorkspaceError, ValueError):
            # Bozuk kontrol noktasi SESSIZCE atlanmaz: silinmez de,
            # cunku tanilama icin gerekebilir. Yalnizca onerilmez.
            continue
        return RecoveryCandidate(
            path=path,
            model=model,
            saved_at=_saved_at(path),
        )
    return None


def discard_checkpoints(root: Path) -> int:
    """Kurtarma kabul edildikten (ya da reddedildikten) sonra temizler.

    Temizlenmezse bir sonraki açılışta aynı öneri tekrar gelir ve
    kullanıcı aynı kararı yeniden vermek zorunda kalır.
    """
    removed = 0
    for path in list_checkpoints(root):
        try:
            path.unlink()
        except OSError:  # pragma: no cover - dosya kilitliyse
            continue
        removed += 1
    return removed


def _prune(directory: Path, keep: int = MAX_CHECKPOINTS) -> None:
    """En yeni `keep` kontrol noktasını bırakır, eskileri siler."""
    found = sorted(
        (
            path
            for path in directory.glob(f"{CHECKPOINT_PREFIX}*{CHECKPOINT_SUFFIX}")
            if path.is_file()
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    for path in found[keep:]:
        try:
            path.unlink()
        except OSError:  # pragma: no cover - dosya kilitliyse
            continue


def _saved_at(path: Path) -> datetime:
    """Dosya adındaki zaman damgası; okunamazsa dosya değişiklik zamanı."""
    stem = path.name[len(CHECKPOINT_PREFIX) : -len(CHECKPOINT_SUFFIX)]
    try:
        return datetime.strptime(stem, "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
