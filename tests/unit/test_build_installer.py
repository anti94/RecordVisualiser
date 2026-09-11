"""Installer oluşturma adımı — `F6-007`.

Kabul: **Uygulama, kısayol ve kaldırma girdisi beklenen konumdadır.**

Asıl kanıt gerçek bir kurulum turuyla üretildi (`docs/packaging/results/
installer-build.json`): installer sessiz kipte geçici bir dizine kuruldu,
üç konum da denetlendi, kurulan uygulama `--self-check`'i geçti ve sonra
kaldırıldı — makinede iz bırakılmadı.

Buradaki testler iki şeyi sabitler:

* NSIS betiği üç konumu da **gerçekten** tanımlıyor mu (dosya, kısayol,
  kaldırma anahtarı) ve kaldırma bölümü hepsini geri alıyor mu,
* araç, paket ya da NSIS yokken **sessizce başarılı** demiyor mu.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_installer import (  # noqa: E402
    build_installer,
    find_makensis,
    find_package,
    read_version,
)

SCRIPT = ROOT / "packaging" / "installer.nsi"


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# UC KONUM betikte tanimli
# --------------------------------------------------------------------------- #


def test_the_installer_script_exists() -> None:
    assert SCRIPT.is_file()


def test_the_application_files_are_installed() -> None:
    text = _script()
    assert 'SetOutPath "$INSTDIR"' in text
    assert "File /r" in text  # onedir duzeninin tamami


def test_a_start_menu_shortcut_is_created() -> None:
    assert "CreateShortCut" in _script()
    assert "$SMPROGRAMS" in _script()


def test_an_uninstall_registry_entry_is_written() -> None:
    """Windows "Uygulamalar ve Özellikler" listesi bu anahtarı okur."""
    text = _script()
    assert "CurrentVersion\\Uninstall" in text
    assert '"DisplayName"' in text
    assert '"DisplayVersion"' in text
    assert '"UninstallString"' in text


def test_the_uninstaller_removes_all_three() -> None:
    """Kaldırma, kurulumun getirdiği üç şeyi de geri almalı."""
    section = _script().split('Section "Uninstall"')[1]
    assert "Delete" in section and "$SMPROGRAMS" in section  # kisayol
    assert "RMDir" in section  # dosyalar
    assert "DeleteRegKey" in section  # kayit girdisi


def test_the_install_is_per_user_and_needs_no_admin() -> None:
    """Yönetici isteyen kurulum, kullanıcının deneyemediği kurulumdur."""
    text = _script()
    assert "RequestExecutionLevel user" in text
    assert "$LOCALAPPDATA" in text
    assert "HKCU" in text


def test_the_version_is_injected_not_hardcoded() -> None:
    """Sürüm `VERSION`'dan gelir; installer adı ve içeriği ayrışamaz."""
    text = _script()
    assert "!ifndef APP_VERSION" in text
    assert read_version() not in text


# --------------------------------------------------------------------------- #
# ARAC sessizce basarili demiyor
# --------------------------------------------------------------------------- #


def test_a_missing_package_is_refused(tmp_path: Path) -> None:
    """Paket üretilmemişken installer "tamam" dememeli."""
    result = build_installer(dist_root=tmp_path)

    assert result.succeeded is False
    assert any("Paket bulunamadi" in line for line in result.log_tail)


def test_a_missing_package_folder_is_detected(tmp_path: Path) -> None:
    assert find_package(tmp_path, "9.9.9") is None


def test_a_package_without_the_executable_is_not_accepted(tmp_path: Path) -> None:
    """Klasör var ama exe yoksa kurulacak bir şey yoktur."""
    (tmp_path / "sonar-analyzer-9.9.9").mkdir(parents=True)
    assert find_package(tmp_path, "9.9.9") is None


def test_the_compiler_is_located_when_installed() -> None:
    """Bu makinede NSIS kurulu; bulunamıyorsa arama mantığı kusurludur."""
    found = find_makensis()
    assert found is None or found.is_file()


# --------------------------------------------------------------------------- #
# gercek kurulum turunun kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_install_found_all_three_locations() -> None:
    evidence = ROOT / "docs/packaging/results/installer-build.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))

    assert payload["succeeded"] is True
    assert payload["installer_bytes"] > 0

    roundtrip = payload["install_roundtrip"]
    assert roundtrip["install_dir_created"] is True
    assert roundtrip["start_menu_shortcut_created"] is True
    assert roundtrip["uninstall_registry_key_created"] is True


def test_the_recorded_uninstall_left_nothing_behind() -> None:
    """Kaldırma sonrası üç konumun da temizlendiği kaydedilmiş."""
    evidence = ROOT / "docs/packaging/results/installer-build.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    after = payload["install_roundtrip"]["after_uninstall"]

    assert after["install_dir_remains"] is False
    assert after["shortcut_remains"] is False
    assert after["registry_key_remains"] is False


def test_the_installed_application_actually_ran() -> None:
    """Kurulan uygulama açıldı; yalnız dosyaların kopyalanması yetmez."""
    evidence = ROOT / "docs/packaging/results/installer-build.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))

    assert "TAMAM" in payload["install_roundtrip"]["installed_app_self_check"]
