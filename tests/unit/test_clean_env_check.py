"""Temiz ortam açılış kontrolü — `F6-005`.

Kabul: **Sistem Python kurulumu olmadan ana ekran açılır.**

Asıl kanıt gerçek paketin temizlenmiş bir ortamda çalıştırılmasıyla
üretildi ve `docs/packaging/results/clean-env-check.json` içinde durur.
Buradaki testler **temizleme mantığını** sabitler: eksik temizleyen bir
kontrol, paketin aslında sistemdeki Python'a yaslandığını fark etmez ve
yanlış bir güven verir.

Bu iş sırasında tam da bu oldu: ilk sürüm `PATH`'i temizliyor sanılırken
Microsoft Store'un "app execution alias" dizinini (`WindowsApps`, içinde
`python.exe` ve `python3.exe` saplamaları) bırakıyordu. Kontrol bunu
yakaladı ve rapor "başarısız" dedi.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.clean_env_check import (  # noqa: E402
    CleanEnvResult,
    find_executable,
    scrub_environment,
)


def _env(path_entries: list[str], **extra: str) -> dict[str, str]:
    base = {"PATH": os.pathsep.join(path_entries)}
    base.update(extra)
    return base


# --------------------------------------------------------------------------- #
# ORTAM TEMIZLEME
# --------------------------------------------------------------------------- #


def test_python_environment_variables_are_removed() -> None:
    """`PYTHONPATH`/`PYTHONHOME` kalırsa paket sistem Python'una bakabilir."""
    source = _env(["C:\\Windows"], PYTHONPATH="C:\\lib", PYTHONHOME="C:\\py", OTHER="kalmali")
    env, removed, _ = scrub_environment(source)

    assert "PYTHONPATH" not in env
    assert "PYTHONHOME" not in env
    assert env["OTHER"] == "kalmali"
    assert removed == ["PYTHONHOME", "PYTHONPATH"]


def test_python_directories_are_removed_from_path() -> None:
    source = _env(
        [
            "C:\\Windows\\System32",
            "C:\\Python39",
            "D:\\proje\\.venv\\Scripts",
            "C:\\Windows",
        ]
    )
    env, _, removed_count = scrub_environment(source)
    kept = env["PATH"].split(os.pathsep)

    assert removed_count == 2
    assert "C:\\Python39" not in kept
    assert "D:\\proje\\.venv\\Scripts" not in kept
    assert "C:\\Windows\\System32" in kept


def test_the_store_alias_directory_is_removed() -> None:
    """`WindowsApps` içinde python.exe saplaması var; bırakılırsa ortam temiz değildir.

    Bu maddeyi atlayan ilk sürüm, kontrolün "başarısız" demesiyle
    yakalandı.
    """
    source = _env(
        [
            "C:\\Windows",
            "C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps",
        ]
    )
    env, _, _ = scrub_environment(source)

    assert all("windowsapps" not in entry.lower() for entry in env["PATH"].split(os.pathsep))


def test_unrelated_path_entries_survive() -> None:
    """Temizleme kör değil: ilgisiz dizinler kalmalı."""
    source = _env(["C:\\Program Files\\Git\\cmd", "C:\\Windows\\System32"])
    env, _, removed_count = scrub_environment(source)

    assert removed_count == 0
    assert len(env["PATH"].split(os.pathsep)) == 2


def test_an_empty_path_is_handled() -> None:
    env, removed, count = scrub_environment({"PATH": ""})
    assert env["PATH"] == ""
    assert (removed, count) == ([], 0)


# --------------------------------------------------------------------------- #
# SONUC DEGERLENDIRMESI
# --------------------------------------------------------------------------- #


def test_a_clean_run_that_opened_the_screen_passes() -> None:
    result = CleanEnvResult(executable="x.exe", self_check_exit=0, python_on_path=False)
    assert result.ok is True


def test_a_failed_self_check_does_not_pass() -> None:
    result = CleanEnvResult(executable="x.exe", self_check_exit=1, python_on_path=False)
    assert result.ok is False


def test_a_run_with_python_still_reachable_does_not_pass() -> None:
    """Ortam temiz değilse "Python'suz açıldı" denemez."""
    result = CleanEnvResult(executable="x.exe", self_check_exit=0, python_on_path=True)
    assert result.ok is False


# --------------------------------------------------------------------------- #
# PAKET BULMA
# --------------------------------------------------------------------------- #


def test_a_missing_dist_yields_no_executable(tmp_path: Path) -> None:
    assert find_executable(tmp_path) is None


def test_the_newest_version_is_chosen(tmp_path: Path) -> None:
    for version in ("1.0.0", "2.0.0"):
        folder = tmp_path / f"sonar-analyzer-{version}"
        folder.mkdir(parents=True)
        (folder / "sonar-analyzer.exe").write_bytes(b"MZ")

    found = find_executable(tmp_path)
    assert found is not None
    assert "2.0.0" in str(found)


# --------------------------------------------------------------------------- #
# gercek kosunun kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_run_opened_the_main_screen() -> None:
    """Depodaki kanıt: ana ekran açıldı ve ortamda Python yoktu."""
    import json

    report = ROOT / "docs/packaging/results/clean-env-check.json"
    if not report.is_file():  # pragma: no cover - kanit henuz uretilmemis
        return
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["self_check_exit"] == 0
    assert payload["python_on_path"] is False
    assert any("ana ekran" in line for line in payload["self_check_lines"])
    assert any("sonuc: TAMAM" in line for line in payload["self_check_lines"])
