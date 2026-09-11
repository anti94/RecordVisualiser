"""Dayanıklılık koşusu değerlendirmesi — `F5-039`.

Kabul: **Bellek bütçesi, beklenen kayıp ve kayıt bütünlüğü sonuçları
kanıtlıdır.**

Bir değerlendiricinin en tehlikeli kusuru her şeye "geçti" demesidir;
böyle bir araç kanıt üretmez, yalnız kanıt üretiyormuş gibi görünür. Bu
yüzden testlerin çoğu **bozuk** girdilerle çalışır ve aracın gerçekten
`sapti` dediğini gösterir: sızıntılı bellek, tutmayan korunum yasası,
CRC kusuru, eksik okunan kayıt.

Gerçek koşunun kararı ayrıca `docs/live/results/endurance-verdict.json`
dosyasındadır; buradaki testler o kararın nasıl verildiğini sabitler.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evaluate_endurance_run import (  # noqa: E402
    DEVIATED,
    INSUFFICIENT,
    PASSED,
    evaluate,
    main,
    render_markdown,
)


def _run(**overrides: Any) -> dict[str, Any]:
    """Sağlıklı bir koşu; testler tek tek bozar."""
    run: dict[str, Any] = {
        "hours": 2.0,
        "windows": 57_600,
        "seed": 7,
        "wall_seconds": 15.0,
        "profile": {"loss_ratio": 0.01},
        "memory": {"samples": 114, "growth_ratio": 1.0034},
        "loss": {
            "produced_windows": 57_600,
            "network_dropped": 600,
            "disk_dropped": 0,
            "recorded_windows": 57_000,
            "observed_missing": 600,
        },
        "integrity": {
            "records_read": 57_000,
            "crc_mismatches": 0,
            "header_failures": 0,
            "trailing_bytes": 0,
            "non_monotonic_records": 0,
        },
        "machine": {"platform": "test", "python": "3.9"},
    }
    run.update(overrides)
    return run


def _status(run: dict[str, Any], name: str) -> str:
    return next(verdict.status for verdict in evaluate(run) if verdict.name == name)


# --------------------------------------------------------------------------- #
# saglikli kosu
# --------------------------------------------------------------------------- #


def test_a_healthy_run_passes_all_three_criteria() -> None:
    assert [verdict.status for verdict in evaluate(_run())] == [PASSED, PASSED, PASSED]


def test_the_three_criteria_are_always_reported() -> None:
    """Hiçbir ölçüt sessizce atlanmaz."""
    names = [verdict.name for verdict in evaluate(_run())]
    assert names == ["bellek butcesi", "beklenen kayip", "kayit butunlugu"]


# --------------------------------------------------------------------------- #
# BELLEK BUTCESI
# --------------------------------------------------------------------------- #


def test_a_memory_leak_is_reported_as_a_deviation() -> None:
    """2 saatte %60 büyüyen bellek "geçti" olamaz."""
    assert _status(_run(memory={"samples": 100, "growth_ratio": 1.6}), "bellek butcesi") == DEVIATED


def test_memory_growth_just_inside_the_limit_passes() -> None:
    assert _status(_run(memory={"samples": 100, "growth_ratio": 1.10}), "bellek butcesi") == PASSED


def test_memory_growth_just_outside_the_limit_deviates() -> None:
    assert (
        _status(_run(memory={"samples": 100, "growth_ratio": 1.101}), "bellek butcesi") == DEVIATED
    )


def test_shrinking_memory_passes() -> None:
    """Bellek küçülüyorsa bütçe sorunu yoktur."""
    assert _status(_run(memory={"samples": 100, "growth_ratio": 0.9}), "bellek butcesi") == PASSED


def test_a_short_run_cannot_judge_the_memory_trend() -> None:
    """Eğilim için 2 saat gerekir; kısa koşu "geçti" diyemez."""
    assert _status(_run(hours=0.1), "bellek butcesi") == INSUFFICIENT


def test_too_few_samples_cannot_judge_the_memory_trend() -> None:
    run = _run(memory={"samples": 3, "growth_ratio": 1.0})
    assert _status(run, "bellek butcesi") == INSUFFICIENT


# --------------------------------------------------------------------------- #
# BEKLENEN KAYIP
# --------------------------------------------------------------------------- #


def test_a_broken_conservation_law_is_a_deviation() -> None:
    """Kaydedilen + düşen, üretileni vermiyorsa pencereler kaybolmuş demektir."""
    loss = _run()["loss"] | {"recorded_windows": 50_000}
    assert _status(_run(loss=loss), "beklenen kayip") == DEVIATED


def test_a_loss_far_above_the_configured_ratio_is_a_deviation() -> None:
    loss = _run()["loss"] | {"network_dropped": 5_000, "recorded_windows": 52_600}
    assert _status(_run(loss=loss), "beklenen kayip") == DEVIATED


def test_a_loss_near_the_configured_ratio_passes() -> None:
    loss = _run()["loss"] | {"network_dropped": 640, "recorded_windows": 56_960}
    assert _status(_run(loss=loss), "beklenen kayip") == PASSED


def test_a_clean_profile_must_lose_nothing() -> None:
    """Bozulma istenmemişken kayıp olmuşsa bu bir sapmadır."""
    loss = _run()["loss"] | {"network_dropped": 5, "recorded_windows": 57_595}
    assert _status(_run(profile={"loss_ratio": 0.0}, loss=loss), "beklenen kayip") == DEVIATED


def test_a_clean_profile_with_no_loss_passes() -> None:
    loss = _run()["loss"] | {"network_dropped": 0, "recorded_windows": 57_600}
    assert _status(_run(profile={"loss_ratio": 0.0}, loss=loss), "beklenen kayip") == PASSED


def test_an_empty_run_cannot_be_judged() -> None:
    loss = _run()["loss"] | {"produced_windows": 0}
    assert _status(_run(loss=loss), "beklenen kayip") == INSUFFICIENT


# --------------------------------------------------------------------------- #
# KAYIT BUTUNLUGU
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "fault",
    ["crc_mismatches", "header_failures", "trailing_bytes", "non_monotonic_records"],
)
def test_any_single_fault_breaks_integrity(fault: str) -> None:
    """Tek bir kusur bile bütünlüğü bozar; hiçbiri tolere edilmez."""
    integrity = _run()["integrity"] | {fault: 1}
    assert _status(_run(integrity=integrity), "kayit butunlugu") == DEVIATED


def test_reading_back_fewer_records_than_written_is_a_deviation() -> None:
    integrity = _run()["integrity"] | {"records_read": 56_000}
    assert _status(_run(integrity=integrity), "kayit butunlugu") == DEVIATED


def test_a_run_without_an_integrity_section_cannot_be_judged() -> None:
    """Ölçüm yoksa "geçti" denmez."""
    assert _status(_run(integrity={}), "kayit butunlugu") == INSUFFICIENT


# --------------------------------------------------------------------------- #
# rapor ve cikis kodu
# --------------------------------------------------------------------------- #


def test_the_markdown_names_every_criterion(tmp_path: Path) -> None:
    text = render_markdown(_run(), evaluate(_run()))
    assert "bellek butcesi" in text
    assert "beklenen kayip" in text
    assert "kayit butunlugu" in text
    assert "2.0 saat" in text


def test_a_healthy_run_exits_zero(tmp_path: Path) -> None:
    source = tmp_path / "run.json"
    source.write_text(json.dumps(_run()), encoding="utf-8")

    assert main(["--run", str(source), "--json", str(tmp_path / "verdict.json")]) == 0


def test_a_deviating_run_exits_non_zero(tmp_path: Path) -> None:
    """Sapma varken sıfır dönmek, süreci sessizce "geçti" saymak olurdu."""
    source = tmp_path / "run.json"
    source.write_text(
        json.dumps(_run(memory={"samples": 100, "growth_ratio": 2.0})), encoding="utf-8"
    )

    assert main(["--run", str(source), "--json", str(tmp_path / "verdict.json")]) == 1


def test_the_verdict_file_is_written(tmp_path: Path) -> None:
    source = tmp_path / "run.json"
    source.write_text(json.dumps(_run()), encoding="utf-8")
    verdict = tmp_path / "nested" / "verdict.json"
    main(["--run", str(source), "--json", str(verdict)])

    payload = json.loads(verdict.read_text(encoding="utf-8"))
    assert [entry["status"] for entry in payload] == [PASSED, PASSED, PASSED]
    assert all(entry["criterion"] for entry in payload)


# --------------------------------------------------------------------------- #
# gercek kosunun karari
# --------------------------------------------------------------------------- #


def test_the_committed_run_passes_every_criterion() -> None:
    """Depodaki gerçek 2 saatlik koşu üç ölçütü de geçer."""
    run = json.loads((ROOT / "docs/live/results/endurance.json").read_text(encoding="utf-8"))
    assert [verdict.status for verdict in evaluate(run)] == [PASSED, PASSED, PASSED]


def test_the_committed_run_is_at_least_two_hours() -> None:
    run = json.loads((ROOT / "docs/live/results/endurance.json").read_text(encoding="utf-8"))
    assert run["hours"] >= 2.0
    assert run["windows"] >= 57_600
