"""Sürümlü ayar yükleme/kaydetme testleri — `F1-009`."""

from __future__ import annotations

import json
from pathlib import Path

from sonar_analyzer.settings.store import (
    SCHEMA_VERSION,
    AppSettings,
    load_settings,
    save_settings,
)


def test_missing_file_yields_defaults_without_warning(tmp_path: Path) -> None:
    result = load_settings(tmp_path / "yok.json")
    assert result.settings == AppSettings()
    assert result.used_defaults is True
    assert result.warnings == [], "dosyanin olmamasi hata degildir"
    assert result.ok


def test_round_trip_preserves_values(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    original = AppSettings(
        theme="light",
        time_display="elapsed",
        last_directory="D:/kayitlar",
        window_geometry="1520x840+10+10",
        recent_files=["a.bin", "b.bin"],
    )
    save_settings(original, target)

    result = load_settings(target)
    assert result.ok
    assert result.settings == original


def test_saved_file_is_readable_json_with_schema_version(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    save_settings(AppSettings(), target)

    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION
    assert target.read_text(encoding="utf-8").endswith("\n")


def test_corrupt_file_falls_back_and_is_quarantined(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text("{ bu gecerli json degil", encoding="utf-8")

    result = load_settings(target)

    assert result.settings == AppSettings()
    assert result.used_defaults is True
    assert len(result.warnings) == 1
    message = result.warnings[0]
    assert "bozuk" in message.lower()
    assert "satir" in message, "kullaniciya nerede bozuldugu soylenmeli"
    assert not target.exists(), "bozuk dosya yerinde birakilmamali"
    assert (tmp_path / "settings.json.bozuk").exists(), "bozuk dosya saklanmali"


def test_non_object_json_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text("[1, 2, 3]", encoding="utf-8")

    result = load_settings(target)
    assert result.settings == AppSettings()
    assert any("beklenen bicimde degil" in w for w in result.warnings)


def test_unknown_values_fall_back_per_field(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "theme": "neon",
                "time_display": "sidereal",
                "last_directory": "D:/kayitlar",
            }
        ),
        encoding="utf-8",
    )

    result = load_settings(target)

    assert result.settings.theme == "dark"
    assert result.settings.time_display == "utc"
    # Gecerli alan korunur; tek bir bozuk alan tum dosyayi cope atmaz.
    assert result.settings.last_directory == "D:/kayitlar"
    assert len(result.warnings) == 2


def test_newer_schema_version_warns_but_loads(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION + 5, "theme": "light"}),
        encoding="utf-8",
    )

    result = load_settings(target)

    assert result.settings.theme == "light"
    assert any("daha yeni bir surumden" in w for w in result.warnings)


def test_missing_schema_version_is_reported(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(json.dumps({"theme": "light"}), encoding="utf-8")

    result = load_settings(target)
    assert result.settings.theme == "light"
    assert any("surum yok" in w for w in result.warnings)


def test_save_does_not_leave_temporary_files(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    save_settings(AppSettings(), target)
    save_settings(AppSettings(theme="light"), target)

    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "settings.json"]
    assert leftovers == [], f"gecici dosya kaldi: {leftovers}"


def test_save_creates_parent_directory(tmp_path: Path) -> None:
    target = tmp_path / "yeni" / "alt" / "settings.json"
    save_settings(AppSettings(), target)
    assert target.exists()
