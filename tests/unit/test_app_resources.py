"""Qt plugin, tema ve ikon kaynakları — `F6-003`.

Kabul: **Paketli açılışta tema, ikon ve platform plugin'i yüklenir.**

Paketin içinde ne olduğu ancak paket çalıştırılarak bilinir; bu yüzden
asıl kanıt `--self-check` ile üretilir ve
`docs/packaging/results/packaging-spike.json` içinde durur. Buradaki
testler o denetimin **mantığını** sabitler: hangi durumda "eksik" dediği,
hangi durumda demediği. Her şeye "tamam" diyen bir denetim, kanıt üretmez.

İkon ayrıca gerçek dosya üzerinde doğrulanır: Windows küçük simge, görev
çubuğu ve büyük simge için farklı boyutlar ister; tek boyutlu bir ikon
ölçeklenip bulanıklaşır.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

from sonar_analyzer.application.self_check import run_self_check
from sonar_analyzer.resources import APP_ICON_NAME, app_icon_path, bundle_root, resource_path

ROOT = Path(__file__).resolve().parents[2]
ICON = ROOT / "packaging" / APP_ICON_NAME


class _FakeApp:
    def __init__(self, *, platform: str = "windows", icon_null: bool = False) -> None:
        self._platform = platform
        self._icon_null = icon_null

    def platformName(self) -> str:
        return self._platform

    def styleSheet(self) -> str:
        return ""

    def windowIcon(self) -> object:
        return _FakeIcon(self._icon_null)


class _FakeIcon:
    def __init__(self, null: bool) -> None:
        self._null = null

    def isNull(self) -> bool:
        return self._null


class _FakeWindow:
    def __init__(self, stylesheet: str = "QWidget { color: red; }") -> None:
        self._stylesheet = stylesheet

    def styleSheet(self) -> str:
        return self._stylesheet


# --------------------------------------------------------------------------- #
# IKON gercek dosya olarak
# --------------------------------------------------------------------------- #


def test_the_icon_file_exists() -> None:
    assert ICON.is_file(), f"ikon uretilmemis: {ICON} (tools/make_app_icon.py)"


def test_the_icon_is_a_valid_ico_container() -> None:
    """ICO başlığı: rezerve=0, tip=1 (ikon), en az bir görüntü."""
    raw = ICON.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", raw[:6])
    assert (reserved, kind) == (0, 1)
    assert count >= 1


def test_the_icon_carries_every_size_windows_asks_for() -> None:
    """16/24/32/48/64/128/256 — tek boyut ölçeklenip bulanıklaşırdı."""
    raw = ICON.read_bytes()
    count = struct.unpack("<H", raw[4:6])[0]
    sizes: set[int] = set()
    for index in range(count):
        offset = 6 + 16 * index
        width = raw[offset]
        sizes.add(256 if width == 0 else width)
    assert sizes == {16, 24, 32, 48, 64, 128, 256}


def test_every_icon_entry_points_inside_the_file() -> None:
    """Dizin girdileri dosyanın dışını göstermemeli."""
    raw = ICON.read_bytes()
    count = struct.unpack("<H", raw[4:6])[0]
    for index in range(count):
        offset = 6 + 16 * index
        size, position = struct.unpack("<II", raw[offset + 8 : offset + 16])
        assert position + size <= len(raw)


# --------------------------------------------------------------------------- #
# KAYNAK YOLU: paket once, sonra kaynak agaci
# --------------------------------------------------------------------------- #


def test_the_icon_is_found_in_the_source_tree() -> None:
    found = app_icon_path()
    assert found is not None
    assert found.name == APP_ICON_NAME


def test_a_missing_resource_returns_none_instead_of_a_wrong_path() -> None:
    """Bulunamayan kaynak sessizce başka bir dosyaya düşmez."""
    assert resource_path("boyle-bir-dosya-yok.bin") is None


def test_an_unfrozen_app_has_no_bundle_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert bundle_root() is None


def test_a_frozen_app_prefers_its_own_bundled_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Paket kendi taşıdığı dosyayı kullanır, geliştirme makinesindekini değil."""
    bundled = tmp_path / APP_ICON_NAME
    bundled.write_bytes(b"sahte-ikon")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert app_icon_path() == bundled


def test_a_frozen_app_falls_back_to_the_source_tree_when_the_bundle_lacks_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    found = app_icon_path()
    assert found is not None
    assert found.parent.name == "packaging"


# --------------------------------------------------------------------------- #
# SELF-CHECK mantigi: eksigi gercekten soyluyor mu
# --------------------------------------------------------------------------- #


def test_a_healthy_startup_reports_everything_loaded() -> None:
    report = run_self_check(_FakeApp(), _FakeWindow())
    assert report.ok is True
    assert "sonuc: TAMAM" in report.lines[-1]


def test_a_missing_platform_plugin_is_reported() -> None:
    """Platform plugin'i yoksa uygulama hiç pencere açamaz; gizlenemez."""
    report = run_self_check(_FakeApp(platform=""), _FakeWindow())
    assert report.ok is False
    assert "platform plugin" in report.failures


def test_a_missing_theme_is_reported() -> None:
    """Boş stil sayfası: çalışır ama mockup'a benzemez — sessiz bozulma."""
    report = run_self_check(_FakeApp(), _FakeWindow(stylesheet=""))
    assert report.ok is False
    assert "tema" in report.failures


def test_an_unloadable_icon_is_reported() -> None:
    report = run_self_check(_FakeApp(icon_null=True), _FakeWindow())
    assert report.ok is False
    assert "ikon" in report.failures


def test_the_report_lists_every_check_even_when_all_pass() -> None:
    """Sessizlik "tamam" anlamına gelmez; üç satır da yazılır."""
    lines = run_self_check(_FakeApp(), _FakeWindow()).lines
    assert any("platform plugin" in line for line in lines)
    assert any("tema" in line for line in lines)
    assert any("ikon" in line for line in lines)


def test_several_faults_are_all_listed() -> None:
    report = run_self_check(_FakeApp(platform="", icon_null=True), _FakeWindow(stylesheet=""))
    assert set(report.failures) == {"platform plugin", "tema", "ikon"}
