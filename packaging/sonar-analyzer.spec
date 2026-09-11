# -*- mode: python ; coding: utf-8 -*-
"""Windows paketleme yapılandırması — `F6-002`.

Kabul: **Giriş noktası, VERSION ve gerekli kaynaklar yapılandırmada
tanımlıdır.**

Araç ve biçim seçimi ADR-012'de gerekçelendirildi: **PyInstaller**,
**onedir**. Bu dosya o kararın yapılandırma karşılığıdır.

Spec bir Python dosyasıdır ve PyInstaller tarafından çalıştırılır; bu
yüzden değerler burada **hesaplanır**, elle kopyalanmaz:

* sürüm depo kökündeki ``VERSION``'dan okunur — paket adı ve gösterilen
  sürüm tek kaynaktan gelir, ikisi ayrışamaz,
* ``VERSION`` ayrıca pakete **veri olarak** konur. `F6-001` spike'ı
  paketlenmiş uygulamanın sürümü bilemediğini (``0.0.0``) gösterdi; dosya
  pakete girmezse uygulama yine bilemez.

Kullanım::

    .venv\\Scripts\\python.exe -m PyInstaller packaging/sonar-analyzer.spec
"""

from pathlib import Path

# Spec dosyasi PyInstaller tarafindan exec edilir; __file__ tanimli degildir,
# ancak SPECPATH saglanir.
ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - PyInstaller enjekte eder

APP_NAME = "sonar-analyzer"
ENTRY_POINT = ROOT / "src" / "sonar_analyzer" / "__main__.py"
VERSION_FILE = ROOT / "VERSION"
ICON_FILE = ROOT / "packaging" / "sonar-analyzer.ico"

APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip()

# Pakete konan veri dosyalari: (kaynak, paket icindeki hedef dizin).
# VERSION kok dizine ("." ) konur; `_bundled_version_file()` orada arar.
DATAS = [(str(VERSION_FILE), ".")]

# Qt platform plugin'i, tema ve ikonlar PySide6/pyqtgraph hook'lariyla
# otomatik toplanir. Toplandiklarinin DOGRULANMASI `F6-003`un isidir;
# burada yalnizca yapilandirma tanimlanir.
HIDDEN_IMPORTS = [
    "sonar_analyzer",
]

analysis = Analysis(  # noqa: F821 - PyInstaller enjekte eder
    [str(ENTRY_POINT)],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Test ve paketleme araclari kullaniciya gitmez.
    excludes=["pytest", "pytest_qt", "PyInstaller", "nuitka"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)  # noqa: F821 - PyInstaller enjekte eder

executable = EXE(  # noqa: F821 - PyInstaller enjekte eder
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX antivirus yanlis pozitiflerini artiriyor
    console=False,  # GUI uygulamasi: acilirken konsol penceresi yanip sonmez
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_FILE) if ICON_FILE.exists() else None,
)

# ADR-012: onefile DEGIL onedir. onefile her acilista kendini gecici bir
# dizine acar; hem acilisi yavaslatir hem antivirus sorunlarini artirir.
collection = COLLECT(  # noqa: F821 - PyInstaller enjekte eder
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=f"{APP_NAME}-{APP_VERSION}",
)
