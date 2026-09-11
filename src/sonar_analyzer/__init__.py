"""SONAR telemetri ve veri analiz arayüzü.

Katmanlar (plan Bölüm 7.1):

    domain       saf veri modelleri, hiçbir G/Ç veya GUI bağımlılığı yok
    io           .bin okuma, decoder, indeks, canlı kaynak
    repository   GUI'nin gördüğü sorgu arayüzü
    processing   DSP ve analiz hattı
    application  komutlar, servisler, playback, workspace
    ui           PySide6 arayüzü — yalnız buradan yukarısı Qt bilir
    export       dışa aktarma
    settings     uygulama ayarları
    plugins      opsiyonel eklentiler

Sürüm tek kaynaktan gelir: depo kökündeki ``VERSION`` dosyası (plan Bölüm 22.1).
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["__version__", "resolve_version", "version"]

_FALLBACK_VERSION = "0.0.0"


def _bundled_version_file() -> Path | None:
    """Paketlenmiş uygulamanın yanına konan ``VERSION`` dosyası — `F6-002`.

    Paketlenmiş uygulamada ne depo ağacı ne de kurulu paket metadata'sı
    bulunur; `F6-001` spike'ında iki paketleyici de bu yüzden **yanlış**
    sürüm bildirdi (`0.0.0` ve `0.21.0`, gerçek sürüm `3.0.0` iken).
    Bu yüzden dosya pakete veri olarak konur ve önce buraya bakılır.

    Yol **`sys._MEIPASS` ile** bulunur. PyInstaller 6, `onedir` kipinde bile
    veri dosyalarını çalıştırılabilirin yanına değil ``_internal`` alt
    dizinine koyar ve ``_MEIPASS``'i oraya gösterir; exe'nin yanına bakmak
    tek başına yetmezdi. ``_MEIPASS`` yoksa (başka bir paketleyici ya da
    ileride değişen bir düzen) çalıştırılabilirin yanı denenir.
    """
    if not getattr(sys, "frozen", False):
        return None
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(sys.executable).resolve().parent
    return root / "VERSION"


def resolve_version() -> str:
    """Sürümü **o anki ortamdan** çözer: paketteki VERSION, kaynak ağacı, metadata.

    ``__version__`` bu fonksiyonun içe aktarma anındaki sonucudur. Fonksiyon
    ayrıca dışa açıktır, çünkü sürümün nereden geldiği paketlenmiş ve
    paketlenmemiş çalıştırmada farklıdır ve bu davranışın sınanabilir olması
    gerekir (`F6-002`).

    Sıra bilerek bu yöndedir. Geliştirme sırasında ``VERSION`` her işte artar; kurulu
    metadata ancak yeniden kurulumda güncellenir. Metadata öncelikli olsaydı sürüm,
    her artıştan sonra yeniden kurulum yapılana kadar eski değeri gösterirdi.

    Wheel'den kurulumda ``VERSION`` paketin yanında bulunmaz ve metadata kullanılır.
    """
    bundled = _bundled_version_file()
    if bundled is not None:
        try:
            text = bundled.read_text(encoding="utf-8").strip()
        except OSError:
            text = ""
        if text:
            return text

    # src/sonar_analyzer/__init__.py -> depo koku
    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        text = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    if text:
        return text

    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _dist_version
    except ImportError:  # pragma: no cover - Python 3.7 ve oncesi
        return _FALLBACK_VERSION

    try:
        return _dist_version("sonar-analyzer")
    except PackageNotFoundError:
        return _FALLBACK_VERSION


__version__ = resolve_version()


def version() -> str:
    """Uygulama sürümünü döndürür."""
    return __version__
