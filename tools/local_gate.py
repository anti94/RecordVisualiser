"""Yerel kalite kapısı — `F6-018`.

Kabul: **Remote varsa gerekli kontroller uygulanır; yoksa yerel eşdeğer
komutlar kayıtlıdır.**

Dal koruması (branch protection) deponun **yönetici ayarıdır** ve
otomatik uygulanamaz; ayrıca uygulanması deponun sahibinin kararıdır.
`docs/ci/quality-gates.md` gerekli kontrolleri ve nasıl açılacağını yazar.

Bu araç o kapıların **yerel eşdeğeridir**: merge öncesi tek komutla aynı
kontrolleri koşturur. Böylece dal koruması açılana kadar (ya da hiç
açılmazsa) kapı yine de bir yerde durur.

Her kontrol **koşar ve sonucu bildirilir**; ilki kırıldığında durulmaz.
Bir geliştiricinin merak ettiği "daha ne kırık" sorusu, tek tek koşarak
öğrenilmemelidir.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Merge oncesi kosan kontroller. Isimler `docs/ci/quality-gates.md` ve
#: `.github/workflows/quality.yml` ile AYNI tutulur; uc yerde farkli isim
#: kullanmak, hangisinin kirildigini aramaya cevirir.
GATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lint", ("-m", "ruff", "check", ".")),
    ("bicim", ("-m", "ruff", "format", "--check", ".")),
    ("tip", ("-m", "pyright")),
    ("test", ("-m", "pytest", "-q", "--no-cov")),
    ("coverage", ("tools/coverage_gate.py",)),
    ("perf-smoke", ("tools/perf_smoke.py",)),
    ("bagimlilik-taramasi", ("tools/dependency_scan.py",)),
    ("todo-sync", ("tools/sync_todo.py", "--check")),
)

#: Coverage kapisi olcum dosyasi ister; once uretilmeli.
COVERAGE_PRODUCER: tuple[str, ...] = (
    "-m",
    "pytest",
    "-q",
    "--cov",
    "--cov-report=json",
    "--cov-report=",
)


@dataclass
class GateResult:
    """Tek bir kapının sonucu."""

    name: str
    exit_code: int
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class GateRun:
    """Bütün kapıların sonucu."""

    results: list[GateResult] = field(default_factory=lambda: [])

    @property
    def failures(self) -> list[GateResult]:
        return [item for item in self.results if not item.ok]

    @property
    def ok(self) -> bool:
        return bool(self.results) and not self.failures


def run_gates(names: tuple[str, ...] = (), *, with_coverage: bool = True) -> GateRun:
    """Kapıları koşturur; **hepsini** koşar, ilk kırıkta durmaz."""
    from time import perf_counter

    run = GateRun()
    selected = [item for item in GATES if not names or item[0] in names]

    if with_coverage and any(name == "coverage" for name, _ in selected):
        # Coverage kapisi coverage.json ister.
        _execute(COVERAGE_PRODUCER)

    for name, argv in selected:
        started = perf_counter()
        code = _execute(argv)
        run.results.append(
            GateResult(name=name, exit_code=code, duration_s=round(perf_counter() - started, 1))
        )
    return run


def _execute(argv: tuple[str, ...]) -> int:
    completed = subprocess.run(
        [sys.executable, *argv],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yerel kalite kapisi (F6-018)")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        metavar="KAPI",
        help=f"yalniz bu kapilar: {', '.join(name for name, _ in GATES)}",
    )
    args = parser.parse_args(argv)

    run = run_gates(tuple(args.only))

    for item in run.results:
        mark = "TAMAM" if item.ok else "KIRIK"
        print(f"  [{mark}] {item.name} ({item.duration_s} s)")
    if run.failures:
        print("kirik kapilar: " + ", ".join(item.name for item in run.failures), file=sys.stderr)
    print("sonuc: " + ("TAMAM" if run.ok else "KAPI KIRIK"))
    return 0 if run.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
