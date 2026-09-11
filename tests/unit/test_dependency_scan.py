"""Bağımlılık güvenlik taraması — `F6-014`.

Kabul: **Tarama raporu üretilir; belirlenen engelleyici sonuçta iş
başarısız olur.**

"Engelleyici" tanımı bu işin asıl kararıydı ve ölçümle şekillendi. İlk
sürüm önemi bilinmeyen bulguları engelleyici sayıyordu; gerçek tarama
15 bulgunun **15'inin** önem bilgisi taşımadığını gösterdi. Sürekli
ateşleyen bir kapı kapatılır ve o günden sonra hiçbir şey yakalamaz.

Ölçüt bu yüzden kesin bir gerçeğe bağlandı: **bulgu kullanıcıya giden bir
bağımlılıkta mı?** Testler kapının hâlâ gerçek olduğunu gösterir —
numpy'de bir açık çıksa iş başarısız olur.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dependency_scan import (  # noqa: E402
    SHIPPED_PACKAGES,
    Finding,
    ScanReport,
    parse_findings,
    scan,
)

EVIDENCE = ROOT / "docs/packaging/results/dependency-scan.json"


def _payload(*entries: tuple[str, str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "dependencies": [
            {"name": name, "version": version, "vulns": vulns} for name, version, vulns in entries
        ]
    }


# --------------------------------------------------------------------------- #
# ENGELLEYICI OLCUTU: kullaniciya giden paket
# --------------------------------------------------------------------------- #


def test_a_vulnerability_in_a_shipped_package_blocks() -> None:
    """numpy kullanıcıya gidiyor; oradaki açık yayını durdurmalı."""
    finding = Finding(package="numpy", version="1.26.0", vulnerability_id="X", severity="low")

    assert finding.shipped is True
    assert finding.blocking is True


def test_a_vulnerability_in_a_dev_tool_does_not_block() -> None:
    """pytest kullanıcıya gitmiyor; geliştirme makinesini ilgilendirir."""
    finding = Finding(package="pytest", version="8.0.0", vulnerability_id="X", severity="critical")

    assert finding.shipped is False
    assert finding.blocking is False


def test_the_severity_does_not_decide() -> None:
    """Kayıtların çoğu önem taşımıyor; ölçüt önem olsaydı kapı işlemezdi."""
    low = Finding(package="scipy", version="1.0", vulnerability_id="X", severity="low")
    unknown = Finding(package="scipy", version="1.0", vulnerability_id="Y", severity="bilinmiyor")

    assert low.blocking is True
    assert unknown.blocking is True


def test_package_names_are_matched_case_insensitively() -> None:
    finding = Finding(package="PySide6", version="6.10.3", vulnerability_id="X", severity="")
    assert finding.blocking is True


def test_the_shipped_list_covers_the_runtime_dependencies() -> None:
    """Kullanıcıya giden her şey listede olmalı; eksik olan denetlenmez."""
    for required in ("numpy", "pyside6", "pyqtgraph", "scipy"):
        assert required in SHIPPED_PACKAGES


def test_the_shipped_list_excludes_development_tools() -> None:
    for tool in ("pytest", "ruff", "pyright", "pip", "setuptools", "pyinstaller"):
        assert tool not in SHIPPED_PACKAGES


# --------------------------------------------------------------------------- #
# RAPOR
# --------------------------------------------------------------------------- #


def test_a_clean_scan_passes() -> None:
    report = ScanReport(scanned=True, packages_scanned=10)
    assert report.ok is True


def test_a_scan_that_never_ran_does_not_pass() -> None:
    """ "Tarayamadım" ile "temiz" aynı şey değildir."""
    assert ScanReport(scanned=False, message="ag yok").ok is False


def test_a_blocking_finding_fails_the_report() -> None:
    report = ScanReport(scanned=True, packages_scanned=10)
    report.findings.append(
        Finding(package="numpy", version="1.0", vulnerability_id="X", severity="")
    )

    assert report.ok is False
    assert len(report.blocking_findings) == 1


def test_informational_findings_are_kept_but_do_not_fail() -> None:
    """Geliştirme aracındaki açık raporlanır; makine de korunmalı."""
    report = ScanReport(scanned=True, packages_scanned=10)
    report.findings.append(Finding(package="pip", version="1.0", vulnerability_id="X", severity=""))

    assert report.ok is True
    assert len(report.informational_findings) == 1


# --------------------------------------------------------------------------- #
# CIKTI COZUMLEME
# --------------------------------------------------------------------------- #


def test_findings_are_parsed_from_the_audit_output() -> None:
    payload = _payload(
        ("numpy", "1.26.0", [{"id": "PYSEC-1", "fix_versions": ["1.26.1"]}]),
        ("scipy", "1.13.0", []),
    )
    count, findings = parse_findings(payload)

    assert count == 2
    assert len(findings) == 1
    assert findings[0].package == "numpy"
    assert findings[0].fix_versions == ["1.26.1"]


def test_a_missing_severity_becomes_the_unknown_label() -> None:
    _count, findings = parse_findings(_payload(("numpy", "1.0", [{"id": "X"}])))
    assert findings[0].severity == "bilinmiyor"


def test_a_scan_whose_output_is_not_json_is_not_counted_as_scanned() -> None:
    def broken(_command: list[str]) -> tuple[int, str]:
        return (2, "ImportError: pip_audit yok")

    report = scan(runner=broken)

    assert report.scanned is False
    assert report.ok is False


def test_a_non_zero_exit_with_valid_json_still_counts_as_scanned() -> None:
    """pip-audit açık bulunca 1 ile çıkar; bu çalışma hatası değildir."""

    def found(_command: list[str]) -> tuple[int, str]:
        return (1, json.dumps(_payload(("pip", "1.0", [{"id": "X"}]))))

    report = scan(runner=found)

    assert report.scanned is True
    assert report.ok is True  # pip kullaniciya gitmiyor


# --------------------------------------------------------------------------- #
# gercek taramanin kaydi
# --------------------------------------------------------------------------- #


def test_the_recorded_scan_actually_ran() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["scanned"] is True
    assert payload["packages_scanned"] > 0


def test_the_recorded_scan_has_no_blocking_finding() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    blocking = [item for item in payload["findings"] if item["package"].lower() in SHIPPED_PACKAGES]

    assert blocking == [], f"kullaniciya giden pakette acik: {blocking}"
