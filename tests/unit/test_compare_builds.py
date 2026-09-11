"""Aynı girdilerle paket üretiminin karşılaştırılması — `F6-010`.

Kabul: **Araç sürümleri ve hash farkları kaydedilir; deterministik
olmayan alanlar açıklanır.**

Gerçek ölçüm iki kez paket üretilerek yapıldı ve
`docs/packaging/results/build-reproducibility.json` içindedir: 291
dosyanın 289'u bit bit aynı, 2'si farklı ve **ikisi de açıklanmış**.

Buradaki testler karşılaştırmanın **ayırt ediciliğini** sabitler. Asıl
tehlike, her farkı "beklenen" sayan bir raporun her şeyi geçirmesidir;
böyle bir rapor, bir gün beklenmedik bir dosya değiştiğinde susar. Bu
yüzden açıklanmamış farkın raporu düşürdüğü ayrıca test edilir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.compare_builds import (  # noqa: E402
    EXPECTED_DIFFERENCES,
    FileDifference,
    ReproducibilityReport,
    compare,
)

EVIDENCE = ROOT / "docs/packaging/results/build-reproducibility.json"


# --------------------------------------------------------------------------- #
# KARSILASTIRMA
# --------------------------------------------------------------------------- #


def test_identical_snapshots_have_no_differences() -> None:
    snapshot = {"a.dll": "hash1", "b/c.pyd": "hash2"}
    assert compare(snapshot, dict(snapshot)) == []


def test_a_changed_file_is_reported() -> None:
    differences = compare({"kitaplik.dll": "aaa"}, {"kitaplik.dll": "bbb"})

    assert len(differences) == 1
    assert differences[0].status == "farkli"
    assert differences[0].first_sha256 == "aaa"
    assert differences[0].second_sha256 == "bbb"


def test_a_file_only_in_one_build_is_reported() -> None:
    """Bir koşuda olup diğerinde olmayan dosya sessizce geçilmemeli."""
    only_first = compare({"tek.dll": "aaa"}, {})
    only_second = compare({}, {"tek.dll": "bbb"})

    assert only_first[0].status == "yalniz_ilk"
    assert only_second[0].status == "yalniz_ikinci"


def test_an_expected_difference_is_marked_with_its_reason() -> None:
    differences = compare({"sonar-analyzer.exe": "aaa"}, {"sonar-analyzer.exe": "bbb"})

    assert differences[0].expected is True
    assert differences[0].reason != ""


def test_an_unexpected_difference_is_not_explained_away() -> None:
    """Listede olmayan bir dosya "beklenen" sayılmamalı."""
    differences = compare({"veri/onemli.bin": "aaa"}, {"veri/onemli.bin": "bbb"})

    assert differences[0].expected is False
    assert differences[0].reason == ""


def test_the_expected_list_is_matched_by_file_name_not_path() -> None:
    """Aynı dosya farklı klasörde de aynı nedenle değişir."""
    differences = compare(
        {"_internal/base_library.zip": "aaa"}, {"_internal/base_library.zip": "bbb"}
    )
    assert differences[0].expected is True


# --------------------------------------------------------------------------- #
# RAPOR: aciklanmamis fark gecmez
# --------------------------------------------------------------------------- #


def test_a_report_with_only_expected_differences_passes() -> None:
    report = ReproducibilityReport(version="1.0.0", total_files=10)
    report.differences.append(
        FileDifference(path="sonar-analyzer.exe", status="farkli", expected=True, reason="zaman")
    )

    assert report.ok is True
    assert report.unexplained == []


def test_a_single_unexplained_difference_fails_the_report() -> None:
    """Her farkı "beklenen" sayan bir rapor hiçbir şey söylemez."""
    report = ReproducibilityReport(version="1.0.0", total_files=10)
    report.differences.append(FileDifference(path="veri.bin", status="farkli", expected=False))

    assert report.ok is False
    assert len(report.unexplained) == 1


def test_a_report_without_any_file_is_not_ok() -> None:
    """Hiç dosya görülmemişse karşılaştırma yapılmamış demektir."""
    assert ReproducibilityReport(version="1.0.0", total_files=0).ok is False


# --------------------------------------------------------------------------- #
# gercek olcumun kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_comparison_has_no_unexplained_difference() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    unexplained = [item for item in payload["differences"] if not item["expected"]]

    assert unexplained == [], f"aciklanmamis fark: {unexplained}"


def test_the_recorded_comparison_kept_almost_everything_identical() -> None:
    """Farkın küçük ve sınırlı olduğu kaydedilmeli."""
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["total_files"] > 0
    assert payload["identical_files"] >= payload["total_files"] - len(payload["differences"])
    assert len(payload["differences"]) < payload["total_files"] * 0.05


def test_the_recorded_comparison_names_the_tool_versions() -> None:
    """Hash farkı araç sürümünden geliyorsa bu sonradan bilinebilmeli."""
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["tools"]["python"]
    assert payload["tools"]["pyinstaller"]


def test_every_recorded_difference_carries_a_reason() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for item in payload["differences"]:
        assert item["reason"], f"{item['path']} icin neden yazilmamis"


def test_the_expected_differences_are_documented_in_code() -> None:
    """Beklenen farklar listesi boş olmamalı ve her biri gerekçeli olmalı."""
    assert EXPECTED_DIFFERENCES
    for name, reason in EXPECTED_DIFFERENCES.items():
        assert reason.strip(), f"{name} icin gerekce yazilmamis"
