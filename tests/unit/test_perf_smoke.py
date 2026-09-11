"""Küçük performans smoke kontrolü — `F6-015`.

Kabul: **Sabit fixture ile bütçe sapması raporlanır.**

Bir smoke kontrolünün iki karşıt kusuru vardır ve testler ikisini de
kapatır:

* bütçe o kadar dar olur ki CI'da rastgele kırılır, kapı kapatılır ve
  hiçbir şey yakalamaz;
* bütçe o kadar geniş olur ki hiçbir sapmayı yakalamaz.

İkincisine karşı asıl güvence, **sapmanın gerçekten raporlandığının**
gösterilmesidir: bütçesi aşılan bir ölçüm raporu düşürmelidir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.perf_smoke import (  # noqa: E402
    BUDGETS_MS,
    DEFAULT_FIXTURE,
    Measurement,
    SmokeReport,
    measure,
)

EVIDENCE = ROOT / "docs/perf/results/smoke.json"


# --------------------------------------------------------------------------- #
# SAPMA RAPORLANIR
# --------------------------------------------------------------------------- #


def test_a_measurement_inside_its_budget_passes() -> None:
    assert Measurement("query", best_ms=10.0, budget_ms=250.0).ok is True


def test_a_measurement_over_its_budget_is_a_deviation() -> None:
    """Bütçeyi aşan ölçüm sessizce geçmemeli."""
    assert Measurement("query", best_ms=300.0, budget_ms=250.0).ok is False


def test_a_measurement_exactly_at_its_budget_passes() -> None:
    assert Measurement("query", best_ms=250.0, budget_ms=250.0).ok is True


def test_a_single_deviation_fails_the_report() -> None:
    report = SmokeReport()
    report.measurements.append(Measurement("open", 10.0, 500.0))
    report.measurements.append(Measurement("query", 999.0, 250.0))

    assert report.ok is False
    assert [item.name for item in report.deviations] == ["query"]


def test_a_report_without_measurements_is_not_ok() -> None:
    """Hiçbir şey ölçmeden "tamam" denmez."""
    assert SmokeReport().ok is False


def test_the_ratio_shows_how_much_budget_was_used() -> None:
    """Rapor yalnız geçti/kaldı değil, ne kadar yaklaşıldığını da söyler."""
    assert Measurement("query", best_ms=125.0, budget_ms=250.0).ratio == 0.5


# --------------------------------------------------------------------------- #
# BUTCELER
# --------------------------------------------------------------------------- #


def test_every_measured_operation_has_a_budget() -> None:
    for name in ("open", "query", "events"):
        assert name in BUDGETS_MS


def test_the_budgets_are_deliberately_generous() -> None:
    """Dar bütçe CI'da rastgele kırılır ve kapı kapatılır."""
    for name, budget in BUDGETS_MS.items():
        assert budget >= 100.0, f"{name} butcesi CI icin fazla dar"


# --------------------------------------------------------------------------- #
# SABIT FIXTURE uzerinde gercek olcum
# --------------------------------------------------------------------------- #


def test_the_fixture_is_committed_to_the_repository() -> None:
    """Ölçüm sabit bir girdiye dayanmalı; yoksa karşılaştırma anlamsızdır."""
    assert DEFAULT_FIXTURE.is_file()


def test_measuring_the_real_fixture_produces_every_operation(tmp_path: Path) -> None:
    report = measure(DEFAULT_FIXTURE, tmp_path, repeats=2)

    assert [item.name for item in report.measurements] == ["open", "query", "events"]
    assert all(item.best_ms >= 0 for item in report.measurements)


def test_measuring_the_real_fixture_stays_inside_the_budgets(tmp_path: Path) -> None:
    report = measure(DEFAULT_FIXTURE, tmp_path, repeats=2)
    assert report.ok is True, [item.name for item in report.deviations]


def test_the_report_records_the_machine_it_ran_on(tmp_path: Path) -> None:
    """Farklı makinelerin sayıları karıştırılmamalı."""
    report = measure(DEFAULT_FIXTURE, tmp_path, repeats=2)

    assert report.machine["platform"]
    assert report.machine["python"].startswith("3.")


# --------------------------------------------------------------------------- #
# gercek kosunun kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_run_had_no_deviation() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    over_budget = [item for item in payload["measurements"] if item["best_ms"] > item["budget_ms"]]

    assert over_budget == [], f"butce sapmasi: {over_budget}"


def test_the_recorded_run_measured_all_three_operations() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    names = {item["name"] for item in payload["measurements"]}

    assert names == {"open", "query", "events"}
