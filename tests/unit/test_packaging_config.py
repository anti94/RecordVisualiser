"""Windows paketleme yapılandırması — `F6-002`.

Kabul: **Giriş noktası, VERSION ve gerekli kaynaklar yapılandırmada
tanımlıdır.**

Üçü de ayrı ayrı sınanır. En önemlisi `VERSION`: `F6-001` spike'ı
paketlenmiş uygulamanın sürümü **bilemediğini** gösterdi (PyInstaller
`0.0.0`, Nuitka `0.21.0`, gerçek sürüm `3.0.0`). Burada hem dosyanın
pakete konduğu, hem de uygulamanın paketlenmişken oradan okuduğu
doğrulanır — ikisinden biri eksikse sürüm yine yanlış olurdu.

Paketlenmiş çalışma, gerçek bir `.exe` üretmeden, PyInstaller'ın
kullandığı işaretler (``sys.frozen``, ``sys._MEIPASS``) taklit edilerek
sınanır. Gerçek paketin açılışı `F6-005`'in işidir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from sonar_analyzer import resolve_version

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "packaging" / "sonar-analyzer.spec"
PYPROJECT = ROOT / "pyproject.toml"


def _spec() -> str:
    return SPEC.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# GIRIS NOKTASI
# --------------------------------------------------------------------------- #


def test_the_spec_file_exists() -> None:
    assert SPEC.is_file(), f"paketleme yapilandirmasi yok: {SPEC}"


def test_the_entry_point_is_declared_and_real() -> None:
    """Spec'te yazan giriş noktası gerçekten var olan bir dosya olmalı."""
    assert "ENTRY_POINT" in _spec()
    assert (ROOT / "src" / "sonar_analyzer" / "__main__.py").is_file()


def test_the_entry_point_matches_the_installed_console_script() -> None:
    """Paketlenen giriş ile `pip install` girişinin ikisi de `app:main`'e gider."""
    assert 'sonar-analyzer = "sonar_analyzer.app:main"' in PYPROJECT.read_text(encoding="utf-8")
    main_module = (ROOT / "src" / "sonar_analyzer" / "__main__.py").read_text(encoding="utf-8")
    assert "main" in main_module


# --------------------------------------------------------------------------- #
# VERSION
# --------------------------------------------------------------------------- #


def test_the_version_file_is_shipped_as_package_data() -> None:
    """`VERSION` pakete veri olarak konmalı; konmazsa sürüm okunamaz."""
    text = _spec()
    assert "VERSION_FILE" in text
    assert "DATAS" in text
    assert 'str(VERSION_FILE), "."' in text


def test_the_spec_reads_the_version_instead_of_hardcoding_it() -> None:
    """Paket adı ve sürüm tek kaynaktan gelir; elle kopyalanmış bir sürüm yok."""
    text = _spec()
    assert "APP_VERSION = VERSION_FILE.read_text" in text
    current = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert current not in text, "surum spec'e elle yazilmis"


def test_a_frozen_app_reads_the_bundled_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`F6-001`'in kusurunun düzeltmesi: paketlenmişken sürüm doğru okunur."""
    (tmp_path / "VERSION").write_text("9.8.7\n", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert resolve_version() == "9.8.7"


def test_a_frozen_app_without_meipass_falls_back_to_the_executable_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_MEIPASS` yoksa çalıştırılabilirin yanı denenir.

    PyInstaller 6 `onedir` kipinde de `_MEIPASS` verir (ve `_internal`
    dizinini gösterir), yani bu yol o araçta kullanılmaz. Yine de duruyor:
    başka bir paketleyici ya da ileride değişen bir düzen `_MEIPASS`
    vermeyebilir ve uygulama o zaman sürümünü yine bilmeli.
    """
    (tmp_path / "VERSION").write_text("4.5.6\n", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "sonar-analyzer.exe"))

    assert resolve_version() == "4.5.6"


def test_a_frozen_app_without_the_file_does_not_invent_a_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dosya pakete girmediyse sessizce yanlış bir sürüm uydurulmaz."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    # Kaynak agacindaki VERSION'a duser; uydurma bir deger uretmez.
    assert resolve_version() == (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_an_unfrozen_app_ignores_the_bundle_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Geliştirme ortamında paket yolu aranmaz; depo `VERSION`'ı kazanır."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert resolve_version() == (ROOT / "VERSION").read_text(encoding="utf-8").strip()


# --------------------------------------------------------------------------- #
# GEREKLI KAYNAKLAR VE SECIMLER
# --------------------------------------------------------------------------- #


def test_the_spec_follows_the_adr_choice_of_onedir() -> None:
    """ADR-012 `onedir` dedi; spec `COLLECT` ile tek klasör üretir."""
    text = _spec()
    assert "COLLECT(" in text
    assert "onefile" in text  # karar gerekcesiyle birlikte yaziliyor


def test_the_gui_app_does_not_open_a_console_window() -> None:
    assert "console=False" in _spec()


def test_upx_is_disabled_with_a_reason() -> None:
    """UPX antivirüs yanlış pozitiflerini artırır; kapalı ve gerekçesi yazılı."""
    text = _spec()
    assert "upx=False" in text
    assert "antivirus" in text.lower()


def test_test_and_build_tools_are_excluded_from_the_package() -> None:
    """Kullanıcıya test ve paketleme araçları gitmez."""
    text = _spec()
    for unwanted in ("pytest", "PyInstaller", "nuitka"):
        assert unwanted in text.split("excludes=")[1].split("]")[0]


def test_the_icon_is_optional_but_wired() -> None:
    """İkon kaynağı yapılandırmada tanımlı; dosya yoksa paketleme kırılmaz."""
    text = _spec()
    assert "ICON_FILE" in text
    assert "ICON_FILE.exists()" in text


def test_the_packaging_extra_pins_the_builder() -> None:
    """Paketleyici sürümü sabit: değişirse üretilen artefakt da değişir."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert "package = [" in text
    assert "pyinstaller==" in text


def test_the_spec_points_at_the_source_layout() -> None:
    """`src` düzeni paketleyiciye bildirilmeli; yoksa modül bulunamaz."""
    assert 'pathex=[str(ROOT / "src")]' in _spec()
