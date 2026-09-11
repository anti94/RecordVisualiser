"""Küçük performans smoke kontrolü — `F6-015`.

Kabul: **Sabit fixture ile bütçe sapması raporlanır.**

`F4-064`'ün büyük dosya benchmark'ı dakikalar sürer ve her commit'te
koşturulamaz. Bu araç onun **CI'da koşabilen küçük kardeşidir**: sabit,
depoda duran bir fixture üzerinde birkaç temel işlemi ölçer ve bütçeden
sapanı bildirir.

Amaç mutlak hızı kanıtlamak değil — CI makinesi geliştirme makinesinden
yavaş ve değişkendir. Amaç **kaçak bir yavaşlamayı yakalamak**: bir
değişiklik açılışı ya da sorguyu mertebe değiştirecek kadar yavaşlatırsa
görünsün. Bu yüzden bütçeler geniş tutulur; dar bütçe CI'da rastgele
kırılır ve kapı kapatılır.

Ölçülen üç işlem, kullanıcının ilk saniyede yaşadıklarıdır:

* **açma** — dosyayı açıp üst bilgiyi okumak,
* **sorgu** — bir kanalın tamamını istemek,
* **olaylar** — kayıttaki olayları çıkarmak.

Her ölçüm birkaç kez yapılır ve **en iyi** süre alınır: en iyi süre
makinenin gerçek kapasitesine en yakın olanıdır, ortalama ise o sırada
çalışan başka işlerden etkilenir.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from sonar_analyzer.repository.file_repository import FileRecordingRepository  # noqa: E402

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "valid_8records.bin"
DEFAULT_REPORT = ROOT / "docs" / "perf" / "results" / "smoke.json"

#: Olcum basina tekrar sayisi; en iyi sure alinir.
REPEATS = 5

#: Butceler BILEREK genis: CI makinesi yavas ve degiskendir, dar butce
#: rastgele kirilir ve kapi kapatilir. Yakalanmak istenen sey mertebe
#: degistiren bir yavaslama.
BUDGETS_MS: dict[str, float] = {
    "open": 500.0,
    "query": 250.0,
    "events": 250.0,
}


@dataclass
class Measurement:
    """Tek bir işlemin ölçümü."""

    name: str
    best_ms: float
    budget_ms: float

    @property
    def ok(self) -> bool:
        return self.best_ms <= self.budget_ms

    @property
    def ratio(self) -> float:
        """Bütçenin kaçta kaçı kullanıldı."""
        return 0.0 if self.budget_ms == 0 else round(self.best_ms / self.budget_ms, 3)


@dataclass
class SmokeReport:
    """Smoke koşusunun sonucu."""

    fixture: str = ""
    repeats: int = REPEATS
    measurements: list[Measurement] = field(default_factory=lambda: [])
    machine: dict[str, str] = field(default_factory=lambda: {})

    @property
    def deviations(self) -> list[Measurement]:
        return [item for item in self.measurements if not item.ok]

    @property
    def ok(self) -> bool:
        return bool(self.measurements) and not self.deviations


def _best_ms(operation: object, repeats: int = REPEATS) -> float:
    """İşlemi `repeats` kez koşturup en iyi süreyi (ms) döner."""
    best = float("inf")
    for _ in range(repeats):
        started = perf_counter()
        operation()  # type: ignore[operator]
        best = min(best, (perf_counter() - started) * 1000)
    return round(best, 3)


def measure(fixture: Path, work_dir: Path, repeats: int = REPEATS) -> SmokeReport:
    """Sabit fixture üzerinde üç temel işlemi ölçer."""
    work_dir.mkdir(parents=True, exist_ok=True)
    report = SmokeReport(
        fixture=fixture.name,
        repeats=repeats,
        machine={"platform": platform.platform(), "python": platform.python_version()},
    )

    def open_recording() -> FileRecordingRepository:
        repository = FileRecordingRepository()
        repository.open(fixture, cache_path=work_dir / "smoke.sidx")
        return repository

    report.measurements.append(
        Measurement("open", _best_ms(open_recording, repeats), BUDGETS_MS["open"])
    )

    repository = open_recording()
    span = repository.metadata().time_range
    channel = next(iter(repository.channels()))

    report.measurements.append(
        Measurement(
            "query",
            _best_ms(lambda: repository.query(channel.id, span), repeats),
            BUDGETS_MS["query"],
        )
    )
    report.measurements.append(
        Measurement(
            "events",
            _best_ms(lambda: repository.events(span), repeats),
            BUDGETS_MS["events"],
        )
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kucuk performans smoke kontrolu (F6-015)")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--work", type=Path, default=ROOT / "build" / "perf-smoke")
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--repeats", type=int, default=REPEATS)
    args = parser.parse_args(argv)

    if not args.fixture.is_file():
        print(f"Fixture yok: {args.fixture}", file=sys.stderr)
        return 2

    report = measure(args.fixture, args.work, args.repeats)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")

    print(f"fixture: {report.fixture} ({report.repeats} tekrar, en iyi sure)")
    for item in report.measurements:
        mark = "TAMAM" if item.ok else "SAPMA"
        print(
            f"  [{mark}] {item.name}: {item.best_ms} ms "
            f"(butce {item.budget_ms} ms, kullanim %{item.ratio * 100:.0f})"
        )
    print(f"rapor: {args.json}")
    print("sonuc: " + ("TAMAM" if report.ok else "BUTCE SAPMASI VAR"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
