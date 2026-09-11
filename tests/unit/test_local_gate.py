"""Merge ve yayın kalite kapıları — `F6-018`.

Kabul: **Remote varsa gerekli kontroller uygulanır; yoksa yerel eşdeğer
komutlar kayıtlıdır.**

Dal koruması deponun yönetici ayarıdır ve kod içinden uygulanamaz; bu
depoda da açılmadı ve bu `docs/ci/quality-gates.md`'de açıkça yazılı.
Karşılığı yerel kapıdır: `tools/local_gate.py` aynı kontrolleri tek
komutla koşturur.

Testlerin asıl işi, üç yerin (CI iş akışı, belge, yerel araç) **aynı
kontrolleri** saymasıdır. Ayrıştıklarında yerel kapı "tamam" derken CI
kırılır ve kapıya güven biter.

Bu araç yazılırken gerçek bir kaçak yakalandı: `ruff check .` deponun
tamamında bir hata buluyordu ama dizin dizin koşturulan `--fix`
çağrılarının çıktısı bastırıldığı için görülmemişti.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local_gate import GATES, GateResult, GateRun, run_gates  # noqa: E402

DOC = ROOT / "docs" / "ci" / "quality-gates.md"
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"
PROTECTION = ROOT / "docs" / "ci" / "branch-protection.json"


def _gate_names() -> set[str]:
    return {name for name, _ in GATES}


# --------------------------------------------------------------------------- #
# UC YER AYNI KONTROLLERI SAYIYOR
# --------------------------------------------------------------------------- #


def test_the_document_exists() -> None:
    assert DOC.is_file()


def test_every_local_gate_is_named_in_the_document() -> None:
    """Belge ile araç ayrışırsa, belge yanlış yönlendirir."""
    text = DOC.read_text(encoding="utf-8")
    for name in _gate_names():
        assert name in text, f"{name} belgede yok"


def test_the_local_gates_cover_the_ci_checks() -> None:
    """CI'da koşan her kapının yerel eşdeğeri olmalı."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    names = _gate_names()

    assert "ruff check" in workflow and "lint" in names
    assert "ruff format --check" in workflow and "bicim" in names
    assert "pyright" in workflow and "tip" in names
    assert "pytest" in workflow and "test" in names
    assert "coverage_gate.py" in workflow and "coverage" in names
    assert "perf_smoke.py" in workflow and "perf-smoke" in names
    assert "dependency_scan.py" in workflow and "bagimlilik-taramasi" in names
    assert "sync_todo.py --check" in workflow and "todo-sync" in names


def test_the_document_records_that_protection_was_not_applied() -> None:
    """Uygulanmayan bir koruma "uygulandı" gibi okunmamalı."""
    text = DOC.read_text(encoding="utf-8")

    assert "Bu depoda uygulanmadı" in text
    assert "gh" in text  # neden uygulanamadigi


def test_the_document_lists_the_required_status_checks() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "package-smoke" in text
    assert "todo-sync" in text


def test_the_protection_config_matches_the_documented_checks() -> None:
    """Hazır yapılandırma ile belgedeki liste aynı olmalı."""
    payload = json.loads(PROTECTION.read_text(encoding="utf-8"))
    contexts = payload["required_status_checks"]["contexts"]
    text = DOC.read_text(encoding="utf-8")

    for context in contexts:
        assert context in text, f"{context} belgede yok"


def test_the_protection_config_forbids_force_push() -> None:
    """Korumanın anlamı buysa, ayarında da öyle yazmalı."""
    payload = json.loads(PROTECTION.read_text(encoding="utf-8"))

    assert payload["allow_force_pushes"] is False
    assert payload["allow_deletions"] is False
    assert payload["enforce_admins"] is True


# --------------------------------------------------------------------------- #
# YEREL KAPI: hepsini kosar, ilk kirikta durmaz
# --------------------------------------------------------------------------- #


def test_a_run_with_a_failure_is_not_ok() -> None:
    run = GateRun()
    run.results.append(GateResult("lint", 0))
    run.results.append(GateResult("tip", 1))

    assert run.ok is False
    assert [item.name for item in run.failures] == ["tip"]


def test_an_empty_run_is_not_ok() -> None:
    """Hiçbir kapı koşmamışsa "tamam" denmez."""
    assert GateRun().ok is False


def test_a_fully_passing_run_is_ok() -> None:
    run = GateRun()
    run.results.append(GateResult("lint", 0))

    assert run.ok is True


def test_selecting_a_subset_runs_only_those(monkeypatch: pytest.MonkeyPatch) -> None:
    """`--only` verilen kapıları koşturur; ötekiler atlanır."""
    calls: list[tuple[str, ...]] = []

    def fake(argv: tuple[str, ...]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr("tools.local_gate._execute", fake)
    run = run_gates(("lint", "bicim"), with_coverage=False)

    assert [item.name for item in run.results] == ["lint", "bicim"]
    assert len(calls) == 2


def test_every_gate_runs_even_after_one_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """ "Daha ne kırık" sorusu tek tek koşturarak öğrenilmemeli."""

    def always_failing(_argv: tuple[str, ...]) -> int:
        return 1

    monkeypatch.setattr("tools.local_gate._execute", always_failing)
    run = run_gates(with_coverage=False)

    assert len(run.results) == len(GATES)
    assert len(run.failures) == len(GATES)


def test_the_gate_names_are_stable() -> None:
    """Adlar CI ve belgede geçiyor; sessizce değişmemeli."""
    assert _gate_names() == {
        "lint",
        "bicim",
        "tip",
        "test",
        "coverage",
        "perf-smoke",
        "bagimlilik-taramasi",
        "todo-sync",
    }
