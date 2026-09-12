"""Paketli ana ekran ↔ mockup karşılaştırması — `F6-031`.

Kabul: **Dokuz bölge, hiyerarşi, tema ve çalışan ana analizler kabul
listesini karşılar.**

Karşılaştırmanın kendisi denetlenmelidir. Her ölçüme "TAMAM" diyen bir
kontrol, hiç kontrol olmamasından kötüdür: geçtiğine dair yanlış bir
güven verir.

Bu yüzden testler her maddeyi **bozulmuş bir ölçümle** de besler ve
maddenin gerçekten düştüğünü görür. Ayrıca kaydedilmiş gerçek ölçümün
belgeyle ve kabul listesiyle tutarlı olduğu doğrulanır.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.mockup_compare import CHECKS, evaluate

from sonar_analyzer.application.layout_report import NINE_REGIONS

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / "docs" / "ui" / "results" / "packaged-layout.json"
REPORT = ROOT / "docs" / "ui" / "results" / "packaged-mockup-comparison.json"
DOC = ROOT / "docs" / "ui" / "packaged-mockup-comparison.md"
LAYOUT_MAP = ROOT / "docs" / "ui" / "layout-map.md"


def _layout() -> dict[str, Any]:
    return json.loads(LAYOUT.read_text(encoding="utf-8"))


def _report() -> dict[str, Any]:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _failed(data: dict[str, Any]) -> list[str]:
    return [check.item for check in evaluate(data) if not check.passed]


# --------------------------------------------------------------------------- #
# SOZLESME: DOKUZ BOLGE
# --------------------------------------------------------------------------- #


def test_the_contract_lists_exactly_nine_regions() -> None:
    assert len(NINE_REGIONS) == 9
    assert [row[0] for row in NINE_REGIONS] == list(range(1, 10))


def test_every_contract_region_appears_in_the_layout_map() -> None:
    """Sözleşme belgeden kopmuşsa, ölçüm yanlış şeyi doğrular."""
    text = LAYOUT_MAP.read_text(encoding="utf-8")
    for _number, label, _object_name, _area in NINE_REGIONS:
        head = label.split("/")[0].split(" ve ")[0].strip()
        assert head in text, f"{label} layout-map.md'de yok"


def test_the_expected_areas_match_the_documented_hierarchy() -> None:
    areas: dict[str, int] = {}
    for _number, _label, _object_name, area in NINE_REGIONS:
        areas[area] = areas.get(area, 0) + 1
    assert areas == {"left": 1, "center": 3, "right": 3, "bottom": 2}


# --------------------------------------------------------------------------- #
# KAYITLI OLCUM GERCEK ve TAM
# --------------------------------------------------------------------------- #


def test_the_measurement_exists_and_covers_every_region() -> None:
    rows = _layout()["regions"]
    assert len(rows) == 9
    assert all(row["found"] and row["visible"] for row in rows)


def test_every_region_landed_in_its_expected_area() -> None:
    for row in _layout()["regions"]:
        assert row["actual_area"] == row["expected_area"], row["object_name"]


def test_the_recorded_run_used_the_packaged_executable_of_this_version() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    report = _report()
    assert report["version"] == version
    assert f"sonar-analyzer-{version}" in str(report["executable"])
    assert str(report["executable"]).endswith(".exe")


def test_the_recorded_run_passed_every_check() -> None:
    report = _report()
    assert report["failed_count"] == 0
    assert report["ok"] is True
    assert report["check_count"] == len(CHECKS)


def test_the_analysis_check_used_real_samples_not_an_empty_panel() -> None:
    """Boş bir panelle "analiz çalışıyor" demek, ölçümü anlamsız kılardı."""
    analysis = _layout()["analysis"]
    assert analysis["attempted"] is True
    assert analysis["opened"] is True
    assert analysis["samples"] > 0
    assert analysis["has_spectrum"] is True
    assert analysis["spectrum_points"] > 0


def test_the_theme_measurement_is_a_real_dark_palette() -> None:
    theme = _layout()["theme"]
    assert theme["stylesheet_chars"] >= 200
    assert theme["background_lightness"] <= 127


# --------------------------------------------------------------------------- #
# HER MADDE BOZULMUS OLCUMDE DUSUYOR MU
# --------------------------------------------------------------------------- #


def test_the_checks_pass_on_the_real_measurement() -> None:
    """Önce karşı yön: gerçek ölçümde hiçbir madde düşmemeli."""
    assert _failed(_layout()) == []


def test_a_region_in_the_wrong_area_fails_the_layout_check() -> None:
    data = deepcopy(_layout())
    data["regions"][0]["actual_area"] = "bottom"
    assert "1.1" in _failed(data)
    assert "1.1h" in _failed(data)


def test_an_invisible_region_fails_the_layout_check() -> None:
    data = deepcopy(_layout())
    data["regions"][3]["visible"] = False
    assert "1.1" in _failed(data)


def test_a_collapsed_column_fails_the_width_check() -> None:
    data = deepcopy(_layout())
    data["columns"]["dock_data_explorer"]["width"] = 20
    assert "1.2" in _failed(data)


def test_a_missing_tab_fails_the_tab_check() -> None:
    data = deepcopy(_layout())
    data["tabs"]["titles"] = data["tabs"]["titles"][:6]
    assert "1.3" in _failed(data)


def test_a_wrong_startup_tab_fails_the_tab_check() -> None:
    data = deepcopy(_layout())
    data["tabs"]["current"] = "Report"
    assert "1.3" in _failed(data)


def test_a_light_theme_fails_the_theme_check() -> None:
    """Tema paketten gelmezse Qt açık paletle açılır; bu yakalanmalı."""
    data = deepcopy(_layout())
    data["theme"]["background_lightness"] = 240
    assert "1.7" in _failed(data)


def test_a_missing_stylesheet_fails_the_theme_check() -> None:
    data = deepcopy(_layout())
    data["theme"]["stylesheet_chars"] = 0
    assert "1.7" in _failed(data)


def test_an_empty_spectrum_fails_the_analysis_check() -> None:
    data = deepcopy(_layout())
    data["analysis"]["has_spectrum"] = False
    data["analysis"]["spectrum_points"] = 0
    assert "3.14" in _failed(data)


def test_enabling_everything_fails_the_v2_placeholder_check() -> None:
    """Pasif olması gereken üç görünüm etkinleşirse bu da bir sapmadır."""
    data = deepcopy(_layout())
    data["tabs"]["enabled"] = list(data["tabs"]["titles"])
    assert "1.3b" in _failed(data)


# --------------------------------------------------------------------------- #
# BELGE OLCUMLE AYNI SEYI SOYLUYOR
# --------------------------------------------------------------------------- #


def test_the_document_reports_the_same_counts_as_the_json() -> None:
    text = DOC.read_text(encoding="utf-8")
    report = _report()
    assert f"**{report['check_count']}**" in text
    assert f"**{report['passed_count']}**" in text
    assert f"**{report['failed_count']}**" in text


def test_the_document_reports_the_measured_column_widths() -> None:
    text = DOC.read_text(encoding="utf-8")
    columns = _layout()["columns"]
    for info in columns.values():
        assert f"{info['width']} px" in text


def test_the_document_names_every_region_object() -> None:
    text = DOC.read_text(encoding="utf-8")
    for _number, _label, object_name, _area in NINE_REGIONS:
        assert f"`{object_name}`" in text


def test_the_document_states_what_the_comparison_does_not_cover() -> None:
    """Kapsam sınırı yazılmazsa, ölçülmeyen şey ölçülmüş sanılır."""
    text = DOC.read_text(encoding="utf-8")
    assert "kapsamadıkları" in text.lower()
    assert "Piksel düzeyinde" in text


def test_the_document_explains_why_the_width_check_is_tolerant() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "tolerans" in text.lower()
    assert "DPI" in text
