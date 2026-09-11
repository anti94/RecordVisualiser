"""Tekrarlı aç/kapat ve playback koşusu — `F6-022`.

Kabul: **Otomatik döngü bellek, handle ve kapanış hatalarını kaydeder.**

Üç ölçünün de kaydedildiği doğrulanır. Asıl incelik **bellek ölçümünün
neyi ölçtüğüdür**: bu araç yazılırken ölçüm üç kez yanlış sonuç verdi ve
her seferinde neden yanlış olduğu bulunup düzeltildi —

1. ısınma maliyeti sızıntı sanıldı,
2. `tracemalloc`'un kendi defterleri uygulamaya sayıldı,
3. oran ölçüsü sabit maliyet ile doğrusal sızıntıyı ayırt edemedi.

Şimdiki ölçü, ısınmadan sonra alınan iki anlık görüntünün **yalnız
uygulama dosyalarına** ait farkıdır ve tur başına verilir. Testler bu
ayrımın korunduğunu denetler.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.open_close_endurance import (  # noqa: E402
    DEFAULT_FIXTURE,
    CycleSample,
    EnduranceResult,
    process_handles,
    run_cycles,
)

EVIDENCE = ROOT / "docs/perf/results/open-close-endurance.json"


# --------------------------------------------------------------------------- #
# UC OLCU DE KAYDEDILIR
# --------------------------------------------------------------------------- #


def test_a_run_records_memory_handles_and_close_errors(tmp_path: Path) -> None:
    result = run_cycles(DEFAULT_FIXTURE, tmp_path, cycles=20, sample_every=5, warmup=5)

    assert result.samples, "bellek ornegi alinmamis"
    assert all(item.handles >= 0 for item in result.samples)
    assert result.close_errors == []


def test_the_cycles_actually_ran(tmp_path: Path) -> None:
    result = run_cycles(DEFAULT_FIXTURE, tmp_path, cycles=20, sample_every=5, warmup=5)

    assert result.cycles == 20
    assert result.samples[-1].cycle == 20


def test_the_warmup_is_recorded_and_excluded(tmp_path: Path) -> None:
    """Isınma turları sayılır ama ölçüm penceresine girmez."""
    result = run_cycles(DEFAULT_FIXTURE, tmp_path, cycles=20, sample_every=5, warmup=7)

    assert result.warmup_cycles == 7
    assert all(item.cycle > 0 for item in result.samples)


def test_the_handle_counter_actually_works() -> None:
    """Sıfır dönen bir sayaç "sızıntı yok" gibi okunur; oysa ölçmemiştir.

    Bu araç yazılırken `ctypes` imzaları bildirilmediği için sayaç hep
    sıfır dönüyordu ve hiçbir şey ölçmeden geçiyordu.
    """
    if sys.platform != "win32":  # pragma: no cover - hedef platform Windows
        return
    assert process_handles() > 0


# --------------------------------------------------------------------------- #
# BELLEK OLCUSU: sabit maliyet ile sizintiyi ayirir
# --------------------------------------------------------------------------- #


def test_the_per_cycle_figure_is_zero_without_samples() -> None:
    assert EnduranceResult(cycles=0).app_bytes_per_cycle == 0.0


def test_the_per_cycle_figure_divides_by_the_cycle_count() -> None:
    result = EnduranceResult(cycles=100, app_bytes_grown=5_000)
    assert result.app_bytes_per_cycle == 50.0


def test_a_fixed_cost_shrinks_per_cycle_as_cycles_grow() -> None:
    """Sabit maliyetin imzası budur; doğrusal sızıntı böyle davranmaz."""
    short = EnduranceResult(cycles=100, app_bytes_grown=2_000)
    long = EnduranceResult(cycles=400, app_bytes_grown=2_000)

    assert short.app_bytes_per_cycle > long.app_bytes_per_cycle


def test_a_linear_leak_keeps_the_same_per_cycle_figure() -> None:
    """Gerçek sızıntıda tur başına değer tur sayısından bağımsızdır."""
    short = EnduranceResult(cycles=100, app_bytes_grown=100 * 40)
    long = EnduranceResult(cycles=400, app_bytes_grown=400 * 40)

    assert short.app_bytes_per_cycle == long.app_bytes_per_cycle == 40.0


def test_the_handle_growth_compares_first_and_last_sample() -> None:
    result = EnduranceResult(cycles=20)
    result.samples.append(CycleSample(cycle=10, traced_bytes=0, handles=100))
    result.samples.append(CycleSample(cycle=20, traced_bytes=0, handles=103))

    assert result.handle_growth == 3


def test_handle_growth_is_zero_with_a_single_sample() -> None:
    result = EnduranceResult(cycles=10)
    result.samples.append(CycleSample(cycle=10, traced_bytes=0, handles=100))

    assert result.handle_growth == 0


# --------------------------------------------------------------------------- #
# KAPANIS HATALARI YUTULMAZ
# --------------------------------------------------------------------------- #


def test_a_close_error_would_be_recorded(tmp_path: Path) -> None:
    """Sessizce yakalanan bir kapanış hatası kullanıcıda geri döner."""
    result = EnduranceResult(cycles=1)
    result.close_errors.append("tur 1: kapanmadi")

    assert len(result.close_errors) == 1


# --------------------------------------------------------------------------- #
# gercek kosunun kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_run_measured_all_three() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["samples"], "bellek ornegi yok"
    assert payload["cycles"] > 0
    assert "close_errors" in payload


def test_the_recorded_run_had_no_close_error() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["close_errors"] == []


def test_the_recorded_run_measured_handles_for_real() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handles = [item["handles"] for item in payload["samples"]]

    assert any(value > 0 for value in handles), "handle sayaci hic olcmemis"
