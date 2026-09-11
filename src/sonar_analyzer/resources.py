"""Paket içi kaynak dosyalarını bulur — `F6-003`.

Uygulama iki farklı düzende çalışır ve kaynak dosyaları iki farklı yerde
durur:

* **kaynak ağacı** — depo kökü (`packaging/sonar-analyzer.ico` gibi),
* **paketlenmiş uygulama** — PyInstaller'ın açtığı dizin.

`F6-001` spike'ı bu ayrımı görmezden gelmenin sonucunu gösterdi: depo
kökünü arayan sürüm okuyucu paketlenmiş uygulamada hiçbir şey bulamadı ve
sürüm `0.0.0` göründü. Kaynaklar için aynı hatayı tekrarlamamak üzere yol
çözümü **tek yerde** toplanır.

Bulunamayan kaynak `None` döner; çağıran taraf kararı kendi verir. Sessizce
boş bir ikon ya da boş bir tema üretmek, eksikliği gizlemek olurdu.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: Depo kökünde kaynakların bulunduğu dizin.
PACKAGING_DIR = "packaging"

#: Uygulama ikonu (`tools/make_app_icon.py` üretir).
APP_ICON_NAME = "sonar-analyzer.ico"


def bundle_root() -> Path | None:
    """Paketlenmiş uygulamanın kaynak dizini; paketlenmemişse `None`.

    PyInstaller 6, `onedir` kipinde bile veri dosyalarını ``_internal``
    altına koyar ve ``sys._MEIPASS``'i oraya gösterir. ``_MEIPASS`` yoksa
    çalıştırılabilirin yanı denenir.
    """
    if not getattr(sys, "frozen", False):
        return None
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(sys.executable).resolve().parent


def source_root() -> Path:
    """Kaynak ağacındaki depo kökü."""
    # src/sonar_analyzer/resources.py -> depo koku
    return Path(__file__).resolve().parents[2]


def resource_path(name: str) -> Path | None:
    """Kaynağı önce pakette, sonra kaynak ağacında arar; yoksa `None`.

    Sıra bilerek bu yöndedir: paketlenmiş uygulama kendi taşıdığı dosyayı
    kullanmalı, geliştirme makinesinde kalmış bir dosyayı değil.
    """
    root = bundle_root()
    if root is not None:
        candidate = root / name
        if candidate.is_file():
            return candidate

    candidate = source_root() / PACKAGING_DIR / name
    return candidate if candidate.is_file() else None


def app_icon_path() -> Path | None:
    """Uygulama ikonunun yolu; pakete girmediyse `None`."""
    return resource_path(APP_ICON_NAME)
