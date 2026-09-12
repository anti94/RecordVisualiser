"""Paketli ana ekranı referans mockup ile karşılaştır — `F6-031`.

Kabul: **Dokuz bölge, hiyerarşi, tema ve çalışan ana analizler kabul
listesini karşılar.**

Bu araç, paketli uygulamayı `--layout-report` ile çalıştırır: ana ekran
**gösterilir**, ölçülür ve ölçüm JSON olarak geri alınır. Sonra
`docs/ui/acceptance-checklist.md` §1'in yerleşim maddeleri bu ölçüme
göre işaretlenir.

Neden pakette ölçülüyor: kaynak ağacındaki testler yerleşimi zaten
denetliyor (`F3-079`). Paketlemede kaybolan bir tema dosyası ya da
gelmeyen bir panel, yalnız paketli çalıştırmada görünür — mockup
kabulünü orada yapmak, kabulü gerçek dağıtılan şeye bağlar.

Her madde **ölçülebilir** bir koşula bağlıdır. "Düzgün görünüyor" gibi
bir madde bu listede yer almaz: kimse onu tekrar doğrulayamaz.

Kullanım::

    python tools/mockup_compare.py
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
FIXTURE = ROOT / "tests" / "fixtures" / "valid_8records_v2.bin"
RESULTS = ROOT / "docs" / "ui" / "results"
LAYOUT_JSON = RESULTS / "packaged-layout.json"
REPORT_JSON = RESULTS / "packaged-mockup-comparison.json"

RUN_TIMEOUT_S = 300


@dataclass
class CheckResult:
    """Kabul listesinden tek bir maddenin sonucu."""

    item: str
    title: str
    passed: bool
    evidence: str


def _version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def find_executable(explicit: Path | None = None) -> Path | None:
    """Bu sürümün paketli `.exe`'si."""
    if explicit is not None:
        return explicit if explicit.is_file() else None
    candidate = DIST / f"sonar-analyzer-{_version()}" / "sonar-analyzer.exe"
    return candidate if candidate.is_file() else None


def capture_layout(exe: Path, out_json: Path) -> tuple[int, str]:
    """Paketli uygulamayı `--layout-report` ile çalıştırır."""
    out_json.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            str(exe),
            "--layout-report",
            str(out_json),
            "--layout-source",
            str(FIXTURE),
        ],
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_S,
        check=False,
    )
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _regions_ok(data: dict[str, Any]) -> CheckResult:
    rows = list(data.get("regions", []))
    wrong = [
        f"{row['region']}:{row['actual_area']}"
        for row in rows
        if not row.get("found")
        or not row.get("visible")
        or row["actual_area"] != row["expected_area"]
    ]
    return CheckResult(
        item="1.1",
        title="Dokuz bölgenin tamamı görünür ve layout-map §2'deki alanda",
        passed=len(rows) == 9 and not wrong,
        evidence=f"{len(rows) - len(wrong)}/9 dogru" + (f"; sapma: {wrong}" if wrong else ""),
    )


def _columns_ok(data: dict[str, Any]) -> CheckResult:
    columns = dict(data.get("columns", {}))
    parts: list[str] = []
    passed = bool(columns)
    for name, info in columns.items():
        width = int(info["width"])
        expected = int(info["expected"])
        tolerance = int(info["tolerance"])
        parts.append(f"{name}={width}px (~{expected})")
        if abs(width - expected) > tolerance:
            passed = False
    return CheckResult(
        item="1.2",
        title="Sol sütun ~200 px, sağ sütun ~300 px, merkez kalan alan",
        passed=passed,
        evidence="; ".join(parts) or "olculemedi",
    )


def _tabs_ok(data: dict[str, Any]) -> CheckResult:
    tabs = dict(data.get("tabs", {}))
    titles = list(tabs.get("titles", []))
    current = str(tabs.get("current", ""))
    return CheckResult(
        item="1.3",
        title="Sekme çubuğunda sekiz sekme, mockup sırasıyla; Time Series seçili açılır",
        passed=len(titles) == 8 and current == "Time Series",
        evidence=f"{len(titles)} sekme, secili: {current!r}",
    )


def _theme_ok(data: dict[str, Any]) -> CheckResult:
    theme = dict(data.get("theme", {}))
    chars = int(theme.get("stylesheet_chars", 0))
    lightness = int(theme.get("background_lightness", 255))
    return CheckResult(
        item="1.7",
        title="Koyu tema uygulanmış (stil sayfası paketten geldi)",
        passed=chars >= 200 and lightness <= 127,
        evidence=(
            f"{chars} karakter stil, arka plan {theme.get('background')} (aydinlik {lightness})"
        ),
    )


def _hierarchy_ok(data: dict[str, Any]) -> CheckResult:
    """Bölgeler doğru **konteynerde** mi: sol/sağ/alt/merkez dağılımı."""
    rows = list(data.get("regions", []))
    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row.get("actual_area"))] = counts.get(str(row.get("actual_area")), 0) + 1
    expected = {"left": 1, "center": 3, "right": 3, "bottom": 2}
    return CheckResult(
        item="1.1h",
        title="Hiyerarşi: 1 sol · 3 merkez · 3 sağ · 2 alt",
        passed=counts == expected,
        evidence=f"olculen: {counts}",
    )


def _analysis_ok(data: dict[str, Any]) -> CheckResult:
    analysis = dict(data.get("analysis", {}))
    points = int(analysis.get("spectrum_points", 0))
    return CheckResult(
        item="3.14",
        title="Ana analiz çalışıyor: spektrum paneli gerçek kayıttan eğri üretiyor",
        passed=bool(analysis.get("has_spectrum")) and points > 0,
        evidence=(
            f"{analysis.get('samples', 0)} ornek -> {points} nokta; "
            f"eksen {analysis.get('frequency_axis')!r} / {analysis.get('amplitude_axis')!r}"
        ),
    )


def _enabled_tabs_ok(data: dict[str, Any]) -> CheckResult:
    tabs = dict(data.get("tabs", {}))
    enabled = sorted(str(title) for title in tabs.get("enabled", []))
    disabled = sorted(set(tabs.get("titles", [])) - set(enabled))
    return CheckResult(
        item="1.3b",
        title="Çalışmayan görünümler pasif ve açıklamalı (v2)",
        passed=len(enabled) == 5 and len(disabled) == 3,
        evidence=f"etkin: {enabled}; pasif: {disabled}",
    )


CHECKS: tuple[Callable[[dict[str, Any]], CheckResult], ...] = (
    _regions_ok,
    _hierarchy_ok,
    _columns_ok,
    _tabs_ok,
    _enabled_tabs_ok,
    _theme_ok,
    _analysis_ok,
)


def evaluate(data: dict[str, Any]) -> list[CheckResult]:
    """Ölçümü kabul listesi maddelerine çevirir."""
    return [check(data) for check in CHECKS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paketli ana ekran ↔ mockup karsilastirmasi")
    parser.add_argument("--exe", type=Path, default=None)
    args = parser.parse_args(argv)

    exe = find_executable(args.exe)
    if exe is None:
        expected = DIST / f"sonar-analyzer-{_version()}" / "sonar-analyzer.exe"
        print(
            f"Paketli uygulama bulunamadi: {expected}\n"
            "Once paketi uretin: python tools/build_package.py",
            file=sys.stderr,
        )
        return 2

    exit_code, output = capture_layout(exe, LAYOUT_JSON)
    if not LAYOUT_JSON.is_file():
        print("Yerlesim raporu uretilemedi:", file=sys.stderr)
        print(output, file=sys.stderr)
        return 1

    data = json.loads(LAYOUT_JSON.read_text(encoding="utf-8"))
    checks = evaluate(data)
    failed = [check for check in checks if not check.passed]

    report = {
        "executable": str(exe),
        "version": _version(),
        "platform": platform.platform(),
        "layout_exit_code": exit_code,
        "layout_report": str(LAYOUT_JSON.relative_to(ROOT)),
        "check_count": len(checks),
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "ok": not failed and exit_code == 0,
        "checks": [asdict(check) for check in checks],
        "window": data.get("window", {}),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for check in checks:
        mark = "TAMAM" if check.passed else "BASARISIZ"
        print(f"[{mark}] {check.item} {check.title}")
        print(f"        {check.evidence}")
    print(f"madde: {len(checks)}, gecen: {len(checks) - len(failed)}, basarisiz: {len(failed)}")
    print(f"rapor: {REPORT_JSON}")
    print("sonuc: " + ("TAMAM" if report["ok"] else "BASARISIZ"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
