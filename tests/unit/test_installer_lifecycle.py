"""Kurulum, yükseltme ve kaldırma — `F6-008`.

Kabul: **Sürüm geçişi kullanıcı workspace ve kaynak kayıtlarını silmez.**

Asıl kanıt gerçek bir turla üretildi (`docs/packaging/results/
installer-lifecycle.json`): 3.6.0 kuruldu, kullanıcı verisi oluşturuldu,
3.7.0 aynı dizine kuruldu, sürümün değiştiği ve verinin durduğu
doğrulandı, sonra kaldırıldı ve verinin **hâlâ** durduğu doğrulandı.

Buradaki testler turun **eksiksizliğini** denetler. Bir yaşam döngüsü
kontrolü, sormadığı soruyu geçmiş sayar: yükseltmede korunan veri
kaldırmada silinebilir, ve yalnız "kuruldu mu" diye soran bir kontrol
bunu hiç görmez.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.installer_lifecycle_check import (  # noqa: E402
    LifecycleReport,
    find_installers,
)

EVIDENCE = ROOT / "docs/packaging/results/installer-lifecycle.json"


def _evidence() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _steps() -> dict[str, dict[str, object]]:
    payload = _evidence()
    steps = payload["steps"]
    assert isinstance(steps, list)
    return {str(step["name"]): step for step in steps}  # type: ignore[index]


# --------------------------------------------------------------------------- #
# TURUN EKSIKSIZLIGI
# --------------------------------------------------------------------------- #


def test_the_recorded_run_covers_install_upgrade_and_uninstall() -> None:
    """Üç aşama da denetlenmiş olmalı; eksik aşama sorulmamış soru demektir."""
    names = set(_steps())

    assert any("kuruldu" in name for name in names)
    assert any("yukseltme" in name for name in names)
    assert any("kaldirma" in name for name in names)


def test_every_recorded_step_passed() -> None:
    failed = [name for name, step in _steps().items() if not step["ok"]]
    assert failed == [], f"basarisiz adimlar: {failed}"


def test_the_version_actually_changed() -> None:
    """Yükseltme yapıldı denmesi yetmez; sürümün değiştiği görülmeli."""
    payload = _evidence()
    assert payload["from_version"] != payload["to_version"]

    step = _steps()["surum degisti"]
    assert step["ok"] is True
    assert "->" in str(step["detail"])


# --------------------------------------------------------------------------- #
# KULLANICI VERISI: iki ayri asamada da korunur
# --------------------------------------------------------------------------- #


def test_the_upgrade_did_not_delete_the_workspace() -> None:
    assert _steps()["yukseltme workspace'i silmedi"]["ok"] is True


def test_the_upgrade_did_not_delete_the_recording() -> None:
    assert _steps()["yukseltme kaydi silmedi"]["ok"] is True


def test_the_uninstall_did_not_delete_the_workspace() -> None:
    """Ayrı bir soru: yükseltmede korunan veri kaldırmada silinebilir."""
    assert _steps()["kaldirma workspace'i silmedi"]["ok"] is True


def test_the_uninstall_did_not_delete_the_recording() -> None:
    assert _steps()["kaldirma kaydi silmedi"]["ok"] is True


def test_the_uninstall_did_remove_the_application() -> None:
    """Kullanıcı verisi kalmalı ama uygulama gitmeli; ikisi karışmamalı."""
    assert _steps()["uygulama dosyalari kaldirildi"]["ok"] is True


# --------------------------------------------------------------------------- #
# RAPOR MANTIGI
# --------------------------------------------------------------------------- #


def test_a_report_with_a_failed_step_is_not_ok() -> None:
    report = LifecycleReport()
    report.add("kuruldu", True)
    report.add("veri korundu", False, "silinmis")

    assert report.ok is False


def test_an_empty_report_is_not_ok() -> None:
    """Hiç adım koşmamış bir tur "geçti" sayılamaz."""
    assert LifecycleReport().ok is False


def test_a_fully_passing_report_is_ok() -> None:
    report = LifecycleReport()
    report.add("kuruldu", True)
    report.add("veri korundu", True)

    assert report.ok is True


# --------------------------------------------------------------------------- #
# INSTALLER BULMA
# --------------------------------------------------------------------------- #


def test_no_installers_in_an_empty_folder(tmp_path: Path) -> None:
    assert find_installers(tmp_path) == []


def test_installers_are_returned_in_version_order(tmp_path: Path) -> None:
    for version in ("3.7.0", "3.6.0"):
        (tmp_path / f"sonar-analyzer-{version}-setup.exe").write_bytes(b"MZ")

    found = [path.name for path in find_installers(tmp_path)]
    assert found[0].endswith("3.6.0-setup.exe")
    assert found[-1].endswith("3.7.0-setup.exe")
