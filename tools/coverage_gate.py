"""Coverage eşikleri — `F6-013`.

Kabul: **Genel en az yüzde 70 ve kritik parser/domain için yüksek eşik
denetlenir.**

Tek bir genel eşik yanıltıcıdır: yüzde 70, kolay kapsanan yüzlerce satırla
sağlanıp `.bin` çözümleyicisinin yüzde 30'da kalmasına izin verir. Bu
yüzden **iki kademe** vardır:

* genel eşik (plan Bölüm 21) — `pyproject.toml`'daki ``fail_under``,
* kritik paketler için daha yüksek eşikler — burada.

Kritik sayılan yerler, yanlış davrandığında **sessizce yanlış veri**
üretebilecek olanlardır: bayt düzeyini çözen `io`, veriyi taşıyan
`domain`, sorguyu karşılayan `repository` ve kaydı yazan `recording`.
Arayüz bu listede yoktur; oradaki bir hata görünür, veriyi bozmaz.

Girdi `coverage json` çıktısıdır; bu araç yalnız okur ve karar verir.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "coverage.json"

#: Genel esik (plan Bolum 21).
OVERALL_THRESHOLD = 70.0

#: Kritik paket -> esik. Yanlis davrandiginda SESSIZCE YANLIS VERI
#: uretebilecek yerler; arayuz bu listede degildir.
CRITICAL_THRESHOLDS: dict[str, float] = {
    "sonar_analyzer/domain": 90.0,
    "sonar_analyzer/io": 85.0,
    "sonar_analyzer/repository": 80.0,
    "sonar_analyzer/recording": 85.0,
}


@dataclass
class GroupResult:
    """Bir paketin (ya da genelin) kapsama sonucu."""

    name: str
    covered: int
    total: int
    percent: float
    threshold: float

    @property
    def ok(self) -> bool:
        return self.percent >= self.threshold


@dataclass
class CoverageGateReport:
    """Bütün eşiklerin sonucu."""

    overall: GroupResult | None = None
    groups: list[GroupResult] = field(default_factory=lambda: [])

    @property
    def failures(self) -> list[GroupResult]:
        items = [] if self.overall is None else [self.overall]
        return [item for item in items + self.groups if not item.ok]

    @property
    def ok(self) -> bool:
        return self.overall is not None and not self.failures


def _normalise(path: str) -> str:
    return path.replace("\\", "/")


def evaluate(data: dict[str, Any]) -> CoverageGateReport:
    """`coverage json` çıktısını eşiklere karşı değerlendirir."""
    report = CoverageGateReport()

    totals = cast("dict[str, Any]", data.get("totals", {}))
    covered = int(totals.get("covered_lines", 0))
    missing = int(totals.get("missing_lines", 0))
    total = covered + missing
    report.overall = GroupResult(
        name="genel",
        covered=covered,
        total=total,
        percent=_percent(covered, total),
        threshold=OVERALL_THRESHOLD,
    )

    files = cast("dict[str, Any]", data.get("files", {}))
    for prefix, threshold in sorted(CRITICAL_THRESHOLDS.items()):
        group_covered = 0
        group_total = 0
        for raw_path, entry in files.items():
            if prefix not in _normalise(raw_path):
                continue
            summary = cast("dict[str, Any]", cast("dict[str, Any]", entry).get("summary", {}))
            group_covered += int(summary.get("covered_lines", 0))
            group_total += int(summary.get("covered_lines", 0)) + int(
                summary.get("missing_lines", 0)
            )
        report.groups.append(
            GroupResult(
                name=prefix,
                covered=group_covered,
                total=group_total,
                percent=_percent(group_covered, group_total),
                threshold=threshold,
            )
        )
    return report


def _percent(covered: int, total: int) -> float:
    """Hiç satır yoksa **sıfır** döner; "veri yok" başarı sayılmaz."""
    return 0.0 if total == 0 else round(covered / total * 100, 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coverage esiklerini denetler (F6-013)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(
            f"Coverage cikti dosyasi yok: {args.input}\n"
            "Once uretin: python -m pytest --cov --cov-report=json",
            file=sys.stderr,
        )
        return 2

    data = cast("dict[str, Any]", json.loads(args.input.read_text(encoding="utf-8")))
    report = evaluate(data)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    rows = ([] if report.overall is None else [report.overall]) + report.groups
    for item in rows:
        mark = "TAMAM" if item.ok else "DUSUK"
        print(
            f"  [{mark}] {item.name}: %{item.percent} "
            f"(esik %{item.threshold}, {item.covered}/{item.total} satir)"
        )
    print("sonuc: " + ("TAMAM" if report.ok else "ESIK ALTINDA"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
