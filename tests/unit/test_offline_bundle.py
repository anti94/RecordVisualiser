"""Offline bağımlılık paketleme — `F6-011`.

Kabul: **Offline hedef varsa bağlantısız kurulum doğrulanır; yoksa koşul
ADR'de gerekçelenir.**

D-16 cevaplanmadığı için **ikisi de** yapıldı: ADR-012'de koşul
gerekçelendirildi *ve* bağlantısız kurulum gerçekten doğrulandı
(`docs/packaging/results/offline-bundle.json`).

Buradaki testler paketin **eksiksizliğini** sabitler. Asıl tuzak,
bağımlılıkları indirip projenin kendisini unutmaktır: klasör dolu görünür,
kurulum yine de çözümlenemez. İlk koşuda tam bu oldu.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.offline_bundle import BUNDLED_EXTRAS, OfflineBundle, download_wheels  # noqa: E402

EVIDENCE = ROOT / "docs/packaging/results/offline-bundle.json"
ADR = ROOT / "docs/adr/ADR-012-packaging.md"


def _evidence() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(EVIDENCE.read_text(encoding="utf-8")))


def _check() -> dict[str, Any]:
    """Bağlantısız çözümleme denetiminin kaydı."""
    check = _evidence()["offline_resolution_check"]
    assert isinstance(check, dict)
    return cast("dict[str, Any]", check)


# --------------------------------------------------------------------------- #
# PAKETIN EKSIKSIZLIGI
# --------------------------------------------------------------------------- #


def test_the_bundle_contains_the_project_itself() -> None:
    """Bağımlılıklar yetmez: proje olmadan kurulum çözümlenemez."""
    wheels = [str(name) for name in _evidence()["wheels"]]
    assert any("sonar_analyzer" in name or "sonar-analyzer" in name for name in wheels)


def test_the_bundle_contains_the_gui_and_dsp_dependencies() -> None:
    wheels = " ".join(str(name).lower() for name in _evidence()["wheels"])

    for required in ("numpy", "pyside6", "pyqtgraph", "scipy"):
        assert required in wheels, f"{required} pakette yok"


def test_the_bundle_records_the_python_and_platform_it_was_made_for() -> None:
    """Wheel'ler platforma özeldir; hangi ortam için indirildiği yazılmalı."""
    payload = _evidence()
    assert str(payload["python"]).startswith("3.")
    assert "Windows" in str(payload["platform"])


def test_the_recorded_bundle_succeeded() -> None:
    payload = _evidence()
    assert payload["succeeded"] is True
    assert int(str(payload["wheel_count"])) > 0
    assert int(str(payload["total_bytes"])) > 0


# --------------------------------------------------------------------------- #
# BAGLANTISIZ KURULUM DOGRULANDI
# --------------------------------------------------------------------------- #


def test_the_offline_resolution_was_checked_without_network() -> None:
    check = _check()
    assert "--no-index" in str(check["command"])
    assert check["exit_code"] == 0


def test_the_offline_check_ignored_already_installed_packages() -> None:
    """Kurulu paketler yok sayılmazsa "zaten var" denip atlanır ve kanıt zayıflar."""
    assert "--ignore-installed" in str(_check()["command"])


def test_the_offline_check_resolved_the_project_and_its_dependencies() -> None:
    would = [str(item).lower() for item in _check()["would_install"]]

    assert any("sonar-analyzer" in item for item in would)
    assert any("pyside6" in item for item in would)
    assert any("numpy" in item for item in would)


# --------------------------------------------------------------------------- #
# ADR gerekcesi
# --------------------------------------------------------------------------- #


def test_the_adr_explains_the_offline_condition() -> None:
    """D-16 cevaplanmadı; koşul ADR'de gerekçelenmiş olmalı."""
    text = ADR.read_text(encoding="utf-8")

    assert "Offline dağıtım" in text
    assert "D-16" in text


def test_the_adr_separates_the_end_user_from_the_build_machine() -> None:
    """İki ihtiyaç karıştırılırsa yanlış iş yapılır."""
    text = ADR.read_text(encoding="utf-8")

    assert "Son kullanıcı zaten offline" in text
    assert "Geliştirici/CI makinesi" in text


# --------------------------------------------------------------------------- #
# ARAC: sessizce basarili demez
# --------------------------------------------------------------------------- #


def test_a_failed_download_is_not_reported_as_success(tmp_path: Path) -> None:
    def failing(_command: list[str]) -> tuple[int, str]:
        return (1, "ERROR: baglanti yok\n")

    bundle = download_wheels(tmp_path, runner=failing)

    assert bundle.succeeded is False
    assert "baglanti yok" in bundle.message


def test_an_empty_folder_is_not_a_bundle(tmp_path: Path) -> None:
    """Çıkış kodu sıfır olsa bile hiçbir paket inmediyse başarı değildir."""

    def silent(_command: list[str]) -> tuple[int, str]:
        return (0, "")

    assert download_wheels(tmp_path, runner=silent).succeeded is False


def test_the_install_command_points_at_the_bundle(tmp_path: Path) -> None:
    bundle = OfflineBundle(output_dir=str(tmp_path))

    assert "--no-index" in bundle.install_command
    assert str(tmp_path) in bundle.install_command


def test_the_bundled_extras_cover_gui_and_dsp() -> None:
    assert "gui" in BUNDLED_EXTRAS
    assert "dsp" in BUNDLED_EXTRAS
