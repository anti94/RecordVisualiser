"""Son açılan dosyalar listesi — `F3-008`.

Liste `AppSettings.recent_files` içinde saklanır (`F1-009`'un sürümlü ayar
dosyası); bu modül yalnız **liste kuralını** tutar, dosya G/Ç yapmaz:

* en son açılan en başta,
* aynı dosya iki kez görünmez (büyük/küçük harf ve yol biçimi farkı
  Windows'ta aynı dosyayı gösterebildiği için `Path` üzerinden karşılaştırılır),
* liste `MAX_RECENT_FILES` ile sınırlıdır — sınırsız büyüyen bir menü
  kullanışlı değildir.

Var olmayan bir girdi listeden **silinmez**: kullanıcı ağ sürücüsü bağlı
değilken de son dosyalarını görmeli. Açılamayan dosya `F3-006`'nın
anlaşılır hatasını verir; kalıcı olarak yok olduğu ancak o zaman anlaşılır
ve `drop()` ile çıkarılır.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

#: Menüde makul kalan uzunluk.
MAX_RECENT_FILES = 10


def _normalized(path: Path) -> str:
    """Karşılaştırma anahtarı: Windows'ta yol biçimi ve harf durumu önemsiz."""
    return str(Path(path)).casefold()


def add(existing: Sequence[str], path: Path, limit: int = MAX_RECENT_FILES) -> list[str]:
    """`path`'i listenin başına koyar; yinelenenleri temizler, sınırı uygular."""
    key = _normalized(path)
    kept = [item for item in existing if _normalized(Path(item)) != key]
    return [str(path), *kept][:limit]


def add_all(
    existing: Sequence[str], paths: Iterable[Path], limit: int = MAX_RECENT_FILES
) -> list[str]:
    """Birden çok dosyayı ekler; **son eklenen en başta** olacak şekilde.

    Çoklu seçimde (`F3-001`) seçim sırası korunsun diye ters sırada
    eklenir: `[a, b, c]` seçildiyse listede `a, b, c` sırasıyla görünür.
    """
    result = list(existing)
    for path in reversed(list(paths)):
        result = add(result, path, limit)
    return result


def drop(existing: Sequence[str], path: Path) -> list[str]:
    """Bir girdiyi listeden çıkarır (örneğin dosya kalıcı olarak yoksa)."""
    key = _normalized(path)
    return [item for item in existing if _normalized(Path(item)) != key]


def default_directory(existing: Sequence[str], fallback: str = "") -> str:
    """Diyaloğun açılacağı klasör: en son açılan dosyanın klasörü."""
    for item in existing:
        parent = Path(item).parent
        if str(parent):
            return str(parent)
    return fallback
