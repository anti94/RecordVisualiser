"""MVP etkileşim bütçesi — `F3-077`.

Kabul: cursor, play/pause, olay gezinmesi ve ağaç sonuçları hedeflerle
karşılaştırılır.

`tools/mvp_interaction_benchmark.py` gerçek `MainWindow` üzerinde dört
etkileşimin medyan gecikmesini ölçer; bu test onu koşturup her ölçümün
`docs/perf/budget.md` §3 hedefinin altında kaldığını doğrular.

**Sınırlama:** offscreen yazılım rasterlayıcısı gerçek ekranı temsil
etmez; sayılar Python + Qt çağrı maliyetidir. Yine de bu ölçümlerin
bütçeyi aşması gerçek bir regresyon işaretidir.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from tools.mvp_interaction_benchmark import BUDGETS, build_report, measure

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return build_report(measure(reps=15))


def _rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(report["measurements"])


def test_every_interaction_has_a_measurement(report: dict[str, Any]) -> None:
    keys = {row["key"] for row in _rows(report)}
    assert keys == {key for key, _label, _budget, _code in BUDGETS}


@pytest.mark.parametrize(("key", "label", "budget_ms", "code"), BUDGETS)
def test_interaction_is_within_budget(
    report: dict[str, Any], key: str, label: str, budget_ms: float, code: str
) -> None:
    row = next(r for r in _rows(report) if r["key"] == key)
    assert row["median_ms"] <= budget_ms, (
        f"{label} ({code}): {row['median_ms']:.2f} ms > {budget_ms} ms bütçesi"
    )


def test_overall_gate_passes(report: dict[str, Any]) -> None:
    assert report["all_pass"] is True
