"""Aç/kapat dayanıklılık sonuçlarını değerlendirir — `F6-023`.

Kabul: **Kalıcı kaynak artışı yoktur veya engelleyici hata işi
açılmıştır.**

`F6-022` ölçtü; bu araç ölçümü **karara** çevirir. Üç ölçüt:

* **bellek** — tur başına **uygulama** belleği artışı bir eşiğin altında
  kalmalı. Oran değil eğim bakılır: kalıcı bir sızıntı doğrusal artar ve
  tur başına değeri sabit kalır, bir kerelik sabit maliyet ise tur sayısı
  büyüdükçe sıfıra yaklaşır. `F6-022` bu ayrımı ölçüye taşıdı.
* **handle** — süreç tanıtıcı sayısı turlar boyunca **artmamalı**.
  Bellekte görünmeyen bir sızıntı (kapanmayan dosya) burada görünür ve
  eşiği dardır: handle sızıntısı her zaman bir kusurdur.
* **kapanış hatası** — sıfır olmalı. Kapanırken atılan bir istisna,
  kullanıcıda "uygulama kapanmıyor" olarak geri döner.

Ölçüt sağlanmıyorsa araç **iş açılmasını ister** ve sıfırdan farklı çıkış
kodu verir; kabulün "veya engelleyici hata işi açılmıştır" yarısı bu
yüzden bir kaçış değil, bir yükümlülüktür.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "docs" / "perf" / "results" / "open-close-endurance.json"
DEFAULT_REPORT = ROOT / "docs" / "perf" / "results" / "open-close-verdict.json"

PASSED = "gecti"
DEVIATED = "sapti"
INSUFFICIENT = "yetersiz"

#: Tur basina uygulama bellegi ust siniri (bayt). 50 bayt/tur, olcum
#: gurultusu icin genis bir paydir; gercek bir sizinti (kapanmayan bir
#: nesne, buyuyen bir liste) bunun kat kat ustunde olur.
MEMORY_PER_CYCLE_LIMIT = 50.0

#: Handle sizintisi her zaman kusurdur; yalniz olcum gurultusu icin
#: kucuk bir pay birakilir.
HANDLE_GROWTH_LIMIT = 2

#: Degerlendirmenin anlamli olmasi icin gereken en az tur ve ornek.
MIN_CYCLES = 50
MIN_SAMPLES = 4


@dataclass
class Verdict:
    """Tek bir ölçütün kararı."""

    name: str
    status: str
    measured: str
    criterion: str
    note: str = ""


@dataclass
class OpenCloseVerdict:
    """Bütün ölçütlerin kararı."""

    verdicts: list[Verdict] = field(default_factory=lambda: [])

    @property
    def deviations(self) -> list[Verdict]:
        return [item for item in self.verdicts if item.status == DEVIATED]

    @property
    def ok(self) -> bool:
        return bool(self.verdicts) and not self.deviations

    @property
    def follow_up_required(self) -> bool:
        """Sapma varsa engelleyici bir iş açılmalıdır."""
        return bool(self.deviations)


def evaluate(run: dict[str, Any]) -> OpenCloseVerdict:
    """Koşu sonucundan üç kararı üretir."""
    report = OpenCloseVerdict()
    cycles = int(run.get("cycles", 0))
    samples = cast("list[Any]", run.get("samples", []))

    if cycles < MIN_CYCLES or len(samples) < MIN_SAMPLES:
        note = f"{cycles} tur, {len(samples)} ornek; en az {MIN_CYCLES} tur gerekli."
        for name in ("bellek", "handle", "kapanis"):
            report.verdicts.append(Verdict(name, INSUFFICIENT, f"{cycles} tur", "-", note))
        return report

    report.verdicts.append(_memory_verdict(run))
    report.verdicts.append(_handle_verdict(samples))
    report.verdicts.append(_close_verdict(run))
    return report


def _memory_verdict(run: dict[str, Any]) -> Verdict:
    cycles = int(run.get("cycles", 0))
    grown = int(run.get("app_bytes_grown", 0))
    criterion = f"tur basina uygulama bellegi <= {MEMORY_PER_CYCLE_LIMIT} bayt"

    if "app_bytes_grown" not in run:
        return Verdict(
            "bellek",
            INSUFFICIENT,
            "olcum yok",
            criterion,
            "Kosu uygulama bellegi olcumu icermiyor (eski surum).",
        )

    per_cycle = 0.0 if cycles <= 0 else round(grown / cycles, 2)
    status = PASSED if per_cycle <= MEMORY_PER_CYCLE_LIMIT else DEVIATED
    note = "" if status == PASSED else f"{cycles} turda {grown} bayt buyudu; kalici bir artis var."
    return Verdict("bellek", status, f"{per_cycle} bayt/tur", criterion, note)


def _handle_verdict(samples: list[Any]) -> Verdict:
    handles = [int(cast("dict[str, Any]", item)["handles"]) for item in samples]
    criterion = f"handle artisi <= {HANDLE_GROWTH_LIMIT}"

    if not any(handles):
        return Verdict(
            "handle",
            INSUFFICIENT,
            "olculemedi",
            criterion,
            "Handle sayaci bu platformda okunamadi.",
        )

    growth = handles[-1] - handles[0]
    status = PASSED if growth <= HANDLE_GROWTH_LIMIT else DEVIATED
    note = "" if status == PASSED else f"{growth} handle sizdi; kapanmayan bir kaynak var."
    return Verdict("handle", status, f"{growth} adet", criterion, note)


def _close_verdict(run: dict[str, Any]) -> Verdict:
    errors = cast("list[Any]", run.get("close_errors", []))
    criterion = "kapanis hatasi = 0"
    status = PASSED if not errors else DEVIATED
    note = "" if status == PASSED else f"Ilk hata: {errors[0]}"
    return Verdict("kapanis", status, f"{len(errors)} hata", criterion, note)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ac/kapat kosusunu degerlendirir (F6-023)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--json", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(
            f"Kosu sonucu yok: {args.input}\nOnce kosturun: python tools/open_close_endurance.py",
            file=sys.stderr,
        )
        return 2

    run = cast("dict[str, Any]", json.loads(args.input.read_text(encoding="utf-8")))
    report = evaluate(run)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps([asdict(item) for item in report.verdicts], indent=2) + "\n",
        encoding="utf-8",
    )

    for item in report.verdicts:
        print(f"  [{item.status}] {item.name}: {item.measured} (kural: {item.criterion})")
        if item.note:
            print(f"            {item.note}")
    if report.follow_up_required:
        print(
            "ENGELLEYICI: sapma var; plan'a bir duzeltme isi acilmali.",
            file=sys.stderr,
        )
    print("sonuc: " + ("TAMAM" if report.ok else "KALICI KAYNAK ARTISI"))
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
