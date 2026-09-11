"""Coverage eşikleri — `F6-013`.

Kabul: **Genel en az yüzde 70 ve kritik parser/domain için yüksek eşik
denetlenir.**

Tek bir genel eşik yanıltıcıdır: yüzde 70, kolay kapsanan yüzlerce
satırla sağlanıp `.bin` çözümleyicisinin yüzde 30'da kalmasına izin
verir. Testler bu yüzden ikinci kademenin **gerçekten ayrı** olduğunu
gösterir: genel eşiği geçen ama kritik paketi düşük bir ölçüm kapıda
kalmalıdır.

Gerçek ölçüm `docs/packaging/results/coverage-gate.json` içindedir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.coverage_gate import (  # noqa: E402
    CRITICAL_THRESHOLDS,
    OVERALL_THRESHOLD,
    evaluate,
)

EVIDENCE = ROOT / "docs/packaging/results/coverage-gate.json"


def _data(overall: tuple[int, int], files: dict[str, tuple[int, int]]) -> dict[str, Any]:
    """`coverage json` biçiminde küçük bir ölçüm kurar."""
    covered, missing = overall
    return {
        "totals": {"covered_lines": covered, "missing_lines": missing},
        "files": {
            path: {"summary": {"covered_lines": value[0], "missing_lines": value[1]}}
            for path, value in files.items()
        },
    }


# --------------------------------------------------------------------------- #
# GENEL ESIK
# --------------------------------------------------------------------------- #


def test_the_overall_threshold_is_the_planned_seventy() -> None:
    assert OVERALL_THRESHOLD == 70.0


def test_an_overall_below_the_threshold_fails() -> None:
    report = evaluate(_data((60, 40), {}))

    assert report.overall is not None
    assert report.overall.percent == 60.0
    assert report.ok is False


def test_an_overall_exactly_at_the_threshold_passes() -> None:
    report = evaluate(_data((70, 30), {}))

    assert report.overall is not None
    assert report.overall.ok is True


def test_a_measurement_with_no_lines_is_not_success() -> None:
    """ "Veri yok" başarı sayılmaz; sıfır yüzde döner."""
    report = evaluate(_data((0, 0), {}))

    assert report.overall is not None
    assert report.overall.percent == 0.0
    assert report.ok is False


# --------------------------------------------------------------------------- #
# KRITIK PAKET ESIKLERI ayri calisir
# --------------------------------------------------------------------------- #


def test_the_critical_packages_are_the_data_path_not_the_ui() -> None:
    """Kritik olan, yanlış davrandığında sessizce yanlış veri üretendir."""
    names = set(CRITICAL_THRESHOLDS)

    assert "sonar_analyzer/domain" in names
    assert "sonar_analyzer/io" in names
    assert "sonar_analyzer/repository" in names
    assert "sonar_analyzer/recording" in names
    assert not any("ui" in name for name in names)


def test_every_critical_threshold_is_higher_than_the_overall_one() -> None:
    for name, threshold in CRITICAL_THRESHOLDS.items():
        assert threshold > OVERALL_THRESHOLD, f"{name} esigi genel esikten yuksek degil"


def test_a_healthy_overall_does_not_hide_a_weak_parser() -> None:
    """Asıl mesele bu: genel geçerken kritik paket düşükse kapı kırılmalı."""
    data = _data(
        (950, 50),  # genel %95
        {"src/sonar_analyzer/io/decoders/binary.py": (30, 70)},  # io %30
    )
    report = evaluate(data)

    assert report.overall is not None and report.overall.ok is True
    assert report.ok is False
    assert any(item.name == "sonar_analyzer/io" for item in report.failures)


def test_a_strong_parser_passes_its_own_threshold() -> None:
    data = _data(
        (950, 50),
        {"src/sonar_analyzer/io/decoders/binary.py": (95, 5)},  # io %95
    )
    report = evaluate(data)
    io_group = next(item for item in report.groups if item.name == "sonar_analyzer/io")

    assert io_group.ok is True


def test_a_critical_package_with_no_measured_line_fails() -> None:
    """Paket hiç ölçülmediyse "geçti" denemez; yüzde sıfır sayılır."""
    report = evaluate(_data((950, 50), {}))
    domain = next(item for item in report.groups if item.name == "sonar_analyzer/domain")

    assert domain.percent == 0.0
    assert domain.ok is False


def test_windows_paths_are_matched_too() -> None:
    """Ölçüm ters bölü ile gelirse eşleşme kaçmamalı."""
    data = _data((950, 50), {"src\\sonar_analyzer\\domain\\channel.py": (95, 5)})
    report = evaluate(data)
    domain = next(item for item in report.groups if item.name == "sonar_analyzer/domain")

    assert domain.total == 100


# --------------------------------------------------------------------------- #
# gercek olcumun kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_run_passed_every_threshold() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["overall"]["percent"] >= OVERALL_THRESHOLD
    for group in payload["groups"]:
        assert group["percent"] >= group["threshold"], f"{group['name']} esik altinda"


def test_the_recorded_run_measured_real_lines() -> None:
    """Boş bir ölçümün "geçti" görünmediğinden emin ol."""
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["overall"]["total"] > 1000
    for group in payload["groups"]:
        assert group["total"] > 0, f"{group['name']} hic olculmemis"
