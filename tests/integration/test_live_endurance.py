"""Uzun süreli canlı kayıt koşusu — `F5-038`.

Kabul: **En az 2 saatlik otomatik koşu bellek, kayıp ve dosya boyutunu
kaydeder.**

Testler koşunun **mekanizmasını** doğrular: üç ölçünün de gerçekten
kaydedildiğini, kayıp kaleminin korunum yasasını sağladığını ve dosya
boyutunun kayıt sayısıyla tutarlı olduğunu. Kısa bir koşuyla sınanır —
2 saatlik koşunun kendisi `tools/live_endurance_run.py` ile ayrıca
yürütülür ve sonucu `docs/live/results/endurance.json` dosyasındadır.

Testin kısa koşması ölçünün değerini düşürmez: ölçülen şeylerin hiçbiri
süreye değil paket sayısına bağlıdır, bu yüzden mekanizma 300 pencerede
de 57 600 pencerede de aynıdır. Kabul kriterinin "en az 2 saat" şartı
komut satırında ayrıca zorlanır ve bu da test edilir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# tools/ paket degildir; kok dizin sys.path'te olunca implicit namespace
# package olarak cozulur (tests/golden_bytes.py ile ayni desen).
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.live_endurance_run import (  # noqa: E402
    DEFAULT_HOURS,
    WINDOWS_PER_HOUR,
    EnduranceResult,
    main,
    run_endurance,
)

from sonar_analyzer.recording.header_writer import header_size_for, record_size_for  # noqa: E402

#: Mekanizmayi sinamak icin yeterli, hizli bir kosu (~0.06 saat).
SHORT_HOURS = 300 / WINDOWS_PER_HOUR


def _run(
    tmp_path: Path,
    *,
    loss_ratio: float = 0.01,
    seed: int = 20260911,
) -> EnduranceResult:
    return run_endurance(tmp_path / "out", hours=SHORT_HOURS, loss_ratio=loss_ratio, seed=seed)


# --------------------------------------------------------------------------- #
# 2 SAAT: kabul kriterinin alt siniri
# --------------------------------------------------------------------------- #


def test_two_hours_is_exactly_57600_windows() -> None:
    """125 ms pencereyle 2 saat = 7200 / 0,125 = 57 600 kayıt."""
    assert WINDOWS_PER_HOUR == 28_800
    assert round(DEFAULT_HOURS * WINDOWS_PER_HOUR) == 57_600


def test_a_shorter_run_than_two_hours_is_refused_on_the_command_line(tmp_path: Path) -> None:
    """Kabul kriteri "en az 2 saat" der; araç daha kısasını kabul etmez."""
    with pytest.raises(SystemExit):
        main(["--hours", "0.5", "--work-dir", str(tmp_path), "--json", str(tmp_path / "r.json")])


# --------------------------------------------------------------------------- #
# BELLEK kaydedilir
# --------------------------------------------------------------------------- #


def test_the_run_records_a_memory_trend(tmp_path: Path) -> None:
    result = _run(tmp_path)
    memory = result.memory

    assert memory.samples > 0
    assert memory.peak_bytes > 0
    assert memory.growth_ratio > 0


def test_the_memory_trend_compares_the_first_and_last_quarter(tmp_path: Path) -> None:
    """Tek bir son değer değil, eğilim kaydedilir."""
    memory = _run(tmp_path).memory
    assert memory.first_quarter_bytes > 0
    assert memory.last_quarter_bytes > 0


# --------------------------------------------------------------------------- #
# KAYIP kaydedilir ve korunur
# --------------------------------------------------------------------------- #


def test_the_loss_breakdown_conserves_every_window(tmp_path: Path) -> None:
    """Üretilen = kaydedilen + ağda düşen + diskte düşen.

    Korunum yasası yazılmasaydı, kaybolan bir pencere hiçbir kaleme
    yazılmadan yok olabilir ve rapor yine de tutarlı görünürdü.
    """
    loss = _run(tmp_path, loss_ratio=0.1).loss
    accounted = loss.recorded_windows + loss.network_dropped + loss.disk_dropped
    assert accounted == loss.produced_windows


def test_a_lossy_run_actually_loses_packets(tmp_path: Path) -> None:
    loss = _run(tmp_path, loss_ratio=0.2).loss
    assert loss.network_dropped > 0
    assert loss.recorded_windows < loss.produced_windows


def test_a_clean_run_loses_nothing(tmp_path: Path) -> None:
    """Bozulma yokken hiçbir pencere kaybolmaz."""
    loss = _run(tmp_path, loss_ratio=0.0).loss
    assert loss.network_dropped == 0
    assert loss.recorded_windows == loss.produced_windows


def test_the_observed_missing_never_exceeds_what_was_dropped(tmp_path: Path) -> None:
    """Sıra izleyici var olmayan kayıp uydurmaz."""
    loss = _run(tmp_path, loss_ratio=0.15).loss
    assert loss.observed_missing <= loss.network_dropped


# --------------------------------------------------------------------------- #
# DOSYA BOYUTU kaydedilir ve kayit sayisiyla tutarlidir
# --------------------------------------------------------------------------- #


def test_the_file_size_matches_what_the_record_count_implies(tmp_path: Path) -> None:
    """Beklenen boyut kayıt sayısından hesaplanır; tutmazsa eksik/fazla var."""
    result = _run(tmp_path)
    files = result.files
    loss = result.loss

    expected = files.files * header_size_for(2) + loss.recorded_windows * record_size_for(2)
    assert files.total_bytes == expected
    assert files.matches_expected is True


def test_the_files_really_exist_on_disk(tmp_path: Path) -> None:
    files = _run(tmp_path).files
    written = sorted((tmp_path / "out").glob("*.bin"))

    assert len(written) == files.files >= 1
    assert [path.stat().st_size for path in written] == files.per_file_bytes


def test_a_small_size_limit_produces_several_files(tmp_path: Path) -> None:
    """Dosya bölünmesi de ölçülür; toplam yine tutarlıdır."""
    result = run_endurance(tmp_path / "out", hours=SHORT_HOURS, max_file_bytes=36 + 50 * 68)
    files = result.files
    loss = result.loss

    assert files.files > 1
    expected = files.files * header_size_for(2) + loss.recorded_windows * record_size_for(2)
    assert files.total_bytes == expected


# --------------------------------------------------------------------------- #
# rapor dosyasi
# --------------------------------------------------------------------------- #


def test_the_report_is_written_as_json(tmp_path: Path) -> None:
    report = tmp_path / "nested" / "endurance.json"
    exit_code = main(
        [
            "--hours",
            str(DEFAULT_HOURS),
            "--work-dir",
            str(tmp_path / "out"),
            "--json",
            str(report),
            "--loss-ratio",
            "0.0",
        ]
    )

    assert exit_code == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["windows"] == 57_600
    assert payload["loss"]["recorded_windows"] == 57_600
    assert payload["machine"]["python"]


def test_the_report_records_the_seed_so_the_run_can_be_repeated(tmp_path: Path) -> None:
    """Seed yazılmazsa koşu tekrar üretilemezdi (`F5-036`)."""
    result = _run(tmp_path, seed=4242)
    assert result.seed == 4242


def test_the_same_seed_gives_the_same_loss_twice(tmp_path: Path) -> None:
    first = run_endurance(tmp_path / "a", hours=SHORT_HOURS, seed=7).loss
    second = run_endurance(tmp_path / "b", hours=SHORT_HOURS, seed=7).loss
    assert first == second
