"""Aç/kapat dayanıklılık değerlendirmesi — `F6-023`.

Kabul: **Kalıcı kaynak artışı yoktur veya engelleyici hata işi
açılmıştır.**

Gerçek koşuda üç ölçüt de geçti: 6,39 bayt/tur uygulama belleği, 0 handle
artışı, 0 kapanış hatası. Sonuç `docs/perf/results/open-close-verdict.json`
dosyasındadır.

Testlerin işi, kararın **ayırt edici** olduğunu göstermek. Bir sızıntı
değerlendiricisinin en tehlikeli hâli her koşuya "geçti" demesidir; bu
yüzden testlerin çoğu sızıntılı ölçümler kurup `sapti` beklendiğini
doğrular — ve sapma varken aracın bir düzeltme işi istediğini.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evaluate_open_close import (  # noqa: E402
    DEVIATED,
    HANDLE_GROWTH_LIMIT,
    INSUFFICIENT,
    MEMORY_PER_CYCLE_LIMIT,
    MIN_CYCLES,
    PASSED,
    evaluate,
)

EVIDENCE = ROOT / "docs/perf/results/open-close-verdict.json"


def _run(**overrides: Any) -> dict[str, Any]:
    run: dict[str, Any] = {
        "cycles": 120,
        "app_bytes_grown": 1_000,
        "close_errors": [],
        "samples": [
            {"cycle": 10, "traced_bytes": 100, "handles": 150},
            {"cycle": 20, "traced_bytes": 100, "handles": 150},
            {"cycle": 30, "traced_bytes": 100, "handles": 150},
            {"cycle": 40, "traced_bytes": 100, "handles": 150},
        ],
    }
    run.update(overrides)
    return run


def _status(run: dict[str, Any], name: str) -> str:
    return next(item.status for item in evaluate(run).verdicts if item.name == name)


# --------------------------------------------------------------------------- #
# SAGLIKLI KOSU
# --------------------------------------------------------------------------- #


def test_a_healthy_run_passes_all_three() -> None:
    report = evaluate(_run())

    assert report.ok is True
    assert report.follow_up_required is False


def test_all_three_criteria_are_always_reported() -> None:
    names = [item.name for item in evaluate(_run()).verdicts]
    assert names == ["bellek", "handle", "kapanis"]


# --------------------------------------------------------------------------- #
# BELLEK
# --------------------------------------------------------------------------- #


def test_a_leak_is_reported_as_a_deviation() -> None:
    """Tur başına 500 bayt, kalıcı bir artıştır."""
    assert _status(_run(app_bytes_grown=120 * 500), "bellek") == DEVIATED


def test_growth_just_inside_the_limit_passes() -> None:
    assert _status(_run(app_bytes_grown=int(120 * MEMORY_PER_CYCLE_LIMIT)), "bellek") == PASSED


def test_growth_just_outside_the_limit_deviates() -> None:
    grown = int(120 * MEMORY_PER_CYCLE_LIMIT) + 120
    assert _status(_run(app_bytes_grown=grown), "bellek") == DEVIATED


def test_a_fixed_cost_spread_over_many_cycles_passes() -> None:
    """Sabit maliyet tur sayısı büyüdükçe eşiğin altına iner."""
    assert _status(_run(cycles=400, app_bytes_grown=2_500), "bellek") == PASSED


def test_a_run_without_the_memory_measurement_cannot_be_judged() -> None:
    """Eski sürüm koşusu "geçti" sayılmamalı."""
    run = _run()
    del run["app_bytes_grown"]
    assert _status(run, "bellek") == INSUFFICIENT


# --------------------------------------------------------------------------- #
# HANDLE
# --------------------------------------------------------------------------- #


def test_a_handle_leak_is_a_deviation() -> None:
    """Kapanmayan dosya bellekte görünmez ama burada görünür."""
    samples = [
        {"cycle": 10, "traced_bytes": 100, "handles": 150},
        {"cycle": 20, "traced_bytes": 100, "handles": 160},
        {"cycle": 30, "traced_bytes": 100, "handles": 170},
        {"cycle": 40, "traced_bytes": 100, "handles": 180},
    ]
    assert _status(_run(samples=samples), "handle") == DEVIATED


def test_a_small_handle_wobble_is_tolerated() -> None:
    samples = [
        {"cycle": 10, "traced_bytes": 100, "handles": 150},
        {"cycle": 20, "traced_bytes": 100, "handles": 151},
        {"cycle": 30, "traced_bytes": 100, "handles": 150},
        {"cycle": 40, "traced_bytes": 100, "handles": 150 + HANDLE_GROWTH_LIMIT},
    ]
    assert _status(_run(samples=samples), "handle") == PASSED


def test_handles_that_were_never_measured_cannot_be_judged() -> None:
    """Sıfır dönen bir sayaç "sızıntı yok" değil, "ölçmedim" demektir."""
    samples = [{"cycle": index * 10, "traced_bytes": 100, "handles": 0} for index in range(1, 5)]
    assert _status(_run(samples=samples), "handle") == INSUFFICIENT


# --------------------------------------------------------------------------- #
# KAPANIS
# --------------------------------------------------------------------------- #


def test_a_close_error_is_a_deviation() -> None:
    assert _status(_run(close_errors=["tur 3: kapanmadi"]), "kapanis") == DEVIATED


def test_no_close_error_passes() -> None:
    assert _status(_run(close_errors=[]), "kapanis") == PASSED


# --------------------------------------------------------------------------- #
# YETERSIZ KOSU ve TAKIP YUKUMLULUGU
# --------------------------------------------------------------------------- #


def test_a_short_run_cannot_be_judged() -> None:
    report = evaluate(_run(cycles=MIN_CYCLES - 1))
    assert all(item.status == INSUFFICIENT for item in report.verdicts)


def test_a_deviation_requires_a_follow_up_task() -> None:
    """Kabulün "veya engelleyici hata işi açılmıştır" yarısı bir yükümlülük."""
    report = evaluate(_run(close_errors=["patladi"]))

    assert report.ok is False
    assert report.follow_up_required is True


# --------------------------------------------------------------------------- #
# gercek kosunun karari
# --------------------------------------------------------------------------- #


def test_the_recorded_verdict_passed_every_criterion() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    deviations = [item for item in payload if item["status"] == DEVIATED]

    assert deviations == [], f"sapma var, duzeltme isi acilmali: {deviations}"


def test_the_recorded_verdict_covers_all_three() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert {item["name"] for item in payload} == {"bellek", "handle", "kapanis"}
