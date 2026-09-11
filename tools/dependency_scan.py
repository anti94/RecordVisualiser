"""Bağımlılık güvenlik taraması — `F6-014`.

Kabul: **Tarama raporu üretilir; belirlenen engelleyici sonuçta iş
başarısız olur.**

Rapor üretip her sonucu geçiren bir tarama, güvenlik işi yapıyormuş gibi
görünür ama hiçbir şey engellemez. Her sonucu engelleyen bir tarama ise
daha kötüdür: sürekli ateşleyen bir kapı kapatılır ve o günden sonra
hiçbir şey yakalamaz. Bu yüzden **engelleyici** tanımı ölçülebilir bir
gerçeğe dayanır:

    Bulgu, **kullanıcıya giden pakette bulunan** bir bağımlılıktaysa
    engelleyicidir.

Ölçüt "önem derecesi" **değildir** ve bu bilinçli bir karardır: PYSEC
kayıtlarının çoğu önem bilgisi taşımaz (bu depoda ölçüldü: 15 bulgunun
15'i "bilinmiyor"). Önemi bilinmeyeni engelleyici saymak kapıyı sürekli
kırmış, düşük saymak ise gerçek bir açığı geçirmiş olurdu; ikisi de
yanlış. Oysa "bu paket kullanıcıya gidiyor mu" sorusunun cevabı kesindir.

Kullanıcıya giden paketler `pyproject.toml`'un çalışma zamanı
bağımlılıklarıdır (`dependencies` + `gui`/`dsp` ekstraları). `pytest`,
`pip`, `setuptools` gibi araçlar geliştirme ortamında kalır; oradaki bir
açık kullanıcıyı etkilemez ama **rapora yine yazılır**, çünkü geliştirme
makinesi de korunmalıdır — yalnız yayını durdurmaz.

Tarama `pip-audit` ile yapılır (PyPI Advisory + OSV veritabanları).
Ağ yoksa tarama **yapılamadı** olarak raporlanır ve iş başarısız olur;
"tarayamadım" ile "temiz" aynı şey değildir.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "docs" / "packaging" / "results" / "dependency-scan.json"

#: Onemi bilinmeyen bulgu icin kullanilan etiket.
UNKNOWN_SEVERITY = "bilinmiyor"

#: Kullaniciya GIDEN paketler. pyproject'teki calisma zamani
#: bagimliliklari ve gui/dsp ekstralari; paketlenmis uygulamanin icinde
#: bunlar bulunur. Liste kod icinde acik tutulur ki bir bagimlilik
#: eklendiginde guvenlik kapisinin kapsamini genisletmek bilincli bir is
#: olsun.
SHIPPED_PACKAGES: frozenset[str] = frozenset(
    {
        "numpy",
        "pyside6",
        "pyside6-addons",
        "pyside6-essentials",
        "shiboken6",
        "pyqtgraph",
        "scipy",
        "pyserial",
    }
)


@dataclass
class Finding:
    """Tek bir güvenlik bulgusu."""

    package: str
    version: str
    vulnerability_id: str
    severity: str
    fix_versions: list[str] = field(default_factory=lambda: [])

    @property
    def shipped(self) -> bool:
        """Bu paket kullanıcıya giden pakette var mı?"""
        return self.package.strip().lower() in SHIPPED_PACKAGES

    @property
    def blocking(self) -> bool:
        """Kullanıcıya giden bir bağımlılıktaki açık akışı durdurur.

        Önem derecesine **bakılmaz**: kayıtların çoğu onu taşımıyor ve
        tahmin etmek iki yönde de yanlış olurdu. Kullanıcıya giden bir
        pakette açık varsa önemi ne olursa olsun bakılmalıdır.
        """
        return self.shipped


@dataclass
class ScanReport:
    """Taramanın sonucu."""

    scanned: bool = False
    exit_code: int = 0
    packages_scanned: int = 0
    findings: list[Finding] = field(default_factory=lambda: [])
    message: str = ""

    @property
    def blocking_findings(self) -> list[Finding]:
        return [item for item in self.findings if item.blocking]

    @property
    def informational_findings(self) -> list[Finding]:
        """Geliştirme araçlarındaki bulgular: raporlanır, yayını durdurmaz."""
        return [item for item in self.findings if not item.blocking]

    @property
    def ok(self) -> bool:
        """Tarama yapılmış **ve** engelleyici bulgu yoksa geçer."""
        return self.scanned and not self.blocking_findings


def _run_pip_audit(command: list[str]) -> tuple[int, str]:
    """pip-audit'i calistirir; YALNIZ stdout doner.

    pip-audit insan okunur ozeti (`Found 15 known vulnerabilities...`)
    stderr'e, JSON'u stdout'a yazar. Ikisi birlestirilirse JSON
    cozumlenemez ve tarama "yapilamadi" sanilir — ilk surumde tam bu oldu.
    """
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return (completed.returncode, completed.stdout or completed.stderr)


def parse_findings(payload: dict[str, Any]) -> tuple[int, list[Finding]]:
    """`pip-audit --format=json` çıktısını bulgulara çevirir."""
    dependencies = cast("list[Any]", payload.get("dependencies", []))
    findings: list[Finding] = []

    for raw in dependencies:
        entry = cast("dict[str, Any]", raw)
        name = str(entry.get("name", ""))
        version = str(entry.get("version", ""))
        for raw_vuln in cast("list[Any]", entry.get("vulns", [])):
            vuln = cast("dict[str, Any]", raw_vuln)
            findings.append(
                Finding(
                    package=name,
                    version=version,
                    vulnerability_id=str(vuln.get("id", "")),
                    severity=str(vuln.get("severity") or UNKNOWN_SEVERITY),
                    fix_versions=[str(item) for item in vuln.get("fix_versions", [])],
                )
            )
    return (len(dependencies), findings)


def scan(runner: Callable[[list[str]], tuple[int, str]] | None = None) -> ScanReport:
    """Kurulu bağımlılıkları tarar."""
    command = [sys.executable, "-m", "pip_audit", "--format=json", "--progress-spinner=off"]
    execute = runner if runner is not None else _run_pip_audit
    exit_code, output = execute(command)

    # pip-audit acik bulunca 1 ile cikar; bu bir CALISMA hatasi degildir.
    # Cikti JSON olarak cozulebiliyorsa tarama yapilmis demektir.
    try:
        payload = cast("dict[str, Any]", json.loads(output[output.index("{") :]))
    except (ValueError, json.JSONDecodeError):
        return ScanReport(
            scanned=False,
            exit_code=exit_code,
            message=(output.strip().splitlines() or ["tarama calistirilamadi"])[-1],
        )

    packages, findings = parse_findings(payload)
    return ScanReport(
        scanned=True,
        exit_code=exit_code,
        packages_scanned=packages,
        findings=findings,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bagimlilik guvenlik taramasi (F6-014)")
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    report = scan()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    if not report.scanned:
        print(f"tarama YAPILAMADI: {report.message}", file=sys.stderr)
        print("sonuc: BASARISIZ (tarayamamak, temiz olmak degildir)", file=sys.stderr)
        return 1

    print(f"taranan paket: {report.packages_scanned}")
    print(
        f"bulgu: {len(report.findings)} "
        f"(engelleyici: {len(report.blocking_findings)}, "
        f"bilgi: {len(report.informational_findings)})"
    )
    for item in report.findings:
        mark = "ENGELLEYICI" if item.blocking else "bilgi (gelistirme araci)"
        fix = f" duzeltme: {', '.join(item.fix_versions)}" if item.fix_versions else ""
        print(
            f"  [{mark}] {item.package} {item.version} — {item.vulnerability_id} "
            f"({item.severity}){fix}"
        )
    print(f"rapor: {args.json}")
    print("sonuc: " + ("TAMAM" if report.ok else "ENGELLEYICI BULGU VAR"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
