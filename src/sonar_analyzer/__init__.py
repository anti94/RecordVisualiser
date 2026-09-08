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

from pathlib import Path

__all__ = ["__version__", "version"]

_FALLBACK_VERSION = "0.0.0"


def _read_version() -> str:
    """Sürümü okur: önce kaynak ağacındaki VERSION dosyası, sonra kurulu paket metadata'sı.

    Sıra bilerek bu yöndedir. Geliştirme sırasında ``VERSION`` her işte artar; kurulu
    metadata ancak yeniden kurulumda güncellenir. Metadata öncelikli olsaydı sürüm,
    her artıştan sonra yeniden kurulum yapılana kadar eski değeri gösterirdi.

    Wheel'den kurulumda ``VERSION`` paketin yanında bulunmaz ve metadata kullanılır.
    """
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


__version__ = _read_version()


def version() -> str:
    """Uygulama sürümünü döndürür."""
    return __version__
