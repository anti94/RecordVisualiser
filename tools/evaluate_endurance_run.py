"""Dayanıklılık koşusunu karara çevirir — `F5-039`.

Kabul: **Bellek bütçesi, beklenen kayıp ve kayıt bütünlüğü sonuçları
kanıtlıdır.**

`F5-038` ölçtü; bu araç ölçümü **karara** çevirir. Üç başlığın her biri
için tek bir durum üretilir:

* `gecti` — ölçülen değer ölçütü karşılıyor,
* `sapti` — sapma var; büyüklüğü yazılır,
* `yetersiz` — bu koşuyla değerlendirilemez.

Karar kuralları burada **açıkça** tanımlıdır ki rapor okunduğunda
"geçti" ne demek tartışmalı olmasın. Ölçüm dosyası değiştirilmez; bu
araç yalnız okur.

Neden bu üç ölçüt
-----------------

* **Bellek** — canlı katman sabit kapasiteli tamponlar kullanır
  (`LiveRingBuffer`, `BoundedPacketQueue`, olay kuyruğu), bu yüzden
  bellek *süreyle* büyümemelidir. Ölçüt son çeyrek / ilk çeyrek oranıdır;
  tek bir tepe değeri değil, çünkü tepe geçici bir tahsisten de gelebilir.
  `docs/perf/budget.md` P-09'un canlı karşılığı budur: orada bellek dosya
  boyutuyla, burada süreyle doğrusal büyümemelidir.
* **Beklenen kayıp** — bozucu (`F5-036`) bilinen bir oranda kayıp üretir;
  gözlenen kayıp bu orana yakın **ve** eksiksiz hesaplanmış olmalıdır.
  Korunum yasası (üretilen = kaydedilen + düşen) olmadan, kaybolan bir
  pencere hiçbir kaleme yazılmadan yok olabilirdi.
* **Kayıt bütünlüğü** — dosyanın okunabildiği ancak okunarak bilinir;
  koşu her kaydı geri okuyup CRC'sini yeniden hesaplar (`F5-038`'in
  `verify_recording` adımı) ve bu araç sonucu karara bağlar.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

PASSED = "gecti"
DEVIATED = "sapti"
INSUFFICIENT = "yetersiz"

#: Bellek "yatay" sayılması için son çeyrek / ilk çeyrek oranı bu sınırın
#: altında olmalı. %10 pay, tahsis edici gürültüsü ve `tracemalloc`'un
#: kendi defterleri içindir; gerçek bir sızıntı 2 saatte bunu çok aşar.
MEMORY_GROWTH_LIMIT = 1.10

#: Gözlenen kayıp oranının beklenen orandan sapabileceği bağıl pay.
#: Kayıp rastgeledir; 57 600 denemede %25 bağıl sapma fazlasıyla geniştir.
LOSS_RELATIVE_TOLERANCE = 0.25

#: Değerlendirmenin anlamlı olması için gereken en kısa koşu.
MIN_HOURS = 2.0


@dataclass
class Verdict:
    """Tek bir ölçütün kararı."""

    name: str
    status: str
    measured: str
    criterion: str
    note: str = ""


def evaluate(run: dict[str, Any]) -> list[Verdict]:
    """Koşu sonucundan üç kararı üretir."""
    return [
        _memory_verdict(run),
        _loss_verdict(run),
        _integrity_verdict(run),
    ]


def _memory_verdict(run: dict[str, Any]) -> Verdict:
    memory = cast("dict[str, Any]", run.get("memory", {}))
    hours = float(run.get("hours", 0.0))
    criterion = f"son ceyrek / ilk ceyrek <= {MEMORY_GROWTH_LIMIT}"

    if hours < MIN_HOURS:
        return Verdict(
            "bellek butcesi",
            INSUFFICIENT,
            f"{hours} saat",
            criterion,
            f"Kosu {MIN_HOURS} saatten kisa; egilim degerlendirilemez.",
        )
    samples = int(memory.get("samples", 0))
    if samples < 8:
        return Verdict(
            "bellek butcesi",
            INSUFFICIENT,
            f"{samples} ornek",
            criterion,
            "Egilim icin yeterli ornek yok.",
        )

    ratio = float(memory.get("growth_ratio", 0.0))
    status = PASSED if ratio <= MEMORY_GROWTH_LIMIT else DEVIATED
    note = "" if status == PASSED else f"Bellek {(ratio - 1.0) * 100:.1f}% buyudu."
    return Verdict("bellek butcesi", status, f"oran {ratio:.4f}", criterion, note)


def _loss_verdict(run: dict[str, Any]) -> Verdict:
    loss = cast("dict[str, Any]", run.get("loss", {}))
    profile = cast("dict[str, Any]", run.get("profile", {}))
    produced = int(loss.get("produced_windows", 0))
    recorded = int(loss.get("recorded_windows", 0))
    network = int(loss.get("network_dropped", 0))
    disk = int(loss.get("disk_dropped", 0))
    expected_ratio = float(profile.get("loss_ratio", 0.0))
    criterion = (
        f"uretilen = kaydedilen + dusen VE gozlenen oran "
        f"{expected_ratio} degerinden en cok %{LOSS_RELATIVE_TOLERANCE * 100:.0f} sapar"
    )

    if produced == 0:
        return Verdict("beklenen kayip", INSUFFICIENT, "0 pencere", criterion, "Kosu bos.")

    accounted = recorded + network + disk
    if accounted != produced:
        return Verdict(
            "beklenen kayip",
            DEVIATED,
            f"{accounted} != {produced}",
            criterion,
            "Korunum yasasi saglanmiyor: pencerelerin hesabi tutmuyor.",
        )

    observed_ratio = network / produced
    if expected_ratio == 0.0:
        status = PASSED if network == 0 else DEVIATED
        return Verdict(
            "beklenen kayip",
            status,
            f"{network} paket",
            criterion,
            "" if status == PASSED else "Bozulma istenmemisken kayip olustu.",
        )

    deviation = abs(observed_ratio - expected_ratio) / expected_ratio
    status = PASSED if deviation <= LOSS_RELATIVE_TOLERANCE else DEVIATED
    note = "" if status == PASSED else f"Gozlenen oran beklenenden %{deviation * 100:.1f} sapti."
    return Verdict(
        "beklenen kayip",
        status,
        f"{observed_ratio:.4f} ({network}/{produced})",
        criterion,
        note,
    )


def _integrity_verdict(run: dict[str, Any]) -> Verdict:
    integrity = cast("dict[str, Any]", run.get("integrity", {}))
    loss = cast("dict[str, Any]", run.get("loss", {}))
    criterion = "her kayit geri okunur, CRC tutar, sira artar, artik bayt yok"

    if not integrity:
        return Verdict(
            "kayit butunlugu",
            INSUFFICIENT,
            "olcum yok",
            criterion,
            "Kosu butunluk dogrulamasi icermiyor.",
        )

    read = int(integrity.get("records_read", 0))
    recorded = int(loss.get("recorded_windows", 0))
    faults = {
        "CRC": int(integrity.get("crc_mismatches", 0)),
        "baslik": int(integrity.get("header_failures", 0)),
        "artik bayt": int(integrity.get("trailing_bytes", 0)),
        "sira": int(integrity.get("non_monotonic_records", 0)),
    }
    broken = [f"{name}={count}" for name, count in faults.items() if count]

    if broken:
        return Verdict(
            "kayit butunlugu",
            DEVIATED,
            f"{read} kayit okundu",
            criterion,
            "Kusur: " + ", ".join(broken),
        )
    if read != recorded:
        return Verdict(
            "kayit butunlugu",
            DEVIATED,
            f"{read} okundu / {recorded} yazildi",
            criterion,
            "Okunan kayit sayisi yazilanla ayni degil.",
        )
    return Verdict("kayit butunlugu", PASSED, f"{read} kayit", criterion)


def render_markdown(run: dict[str, Any], verdicts: list[Verdict]) -> str:
    """Kararları okunur bir tabloya çevirir."""
    machine = cast("dict[str, Any]", run.get("machine", {}))
    lines = [
        "# Dayanıklılık koşusu değerlendirmesi — `F5-039`",
        "",
        f"Koşu: **{run.get('hours')} saat** ({run.get('windows')} pencere), "
        f"seed `{run.get('seed')}`, duvar saati {run.get('wall_seconds')} s.",
        f"Makine: {machine.get('platform')} / Python {machine.get('python')}.",
        "",
        "| Ölçüt | Durum | Ölçülen | Kural | Not |",
        "| --- | --- | --- | --- | --- |",
    ]
    for verdict in verdicts:
        lines.append(
            f"| {verdict.name} | **{verdict.status}** | {verdict.measured} "
            f"| {verdict.criterion} | {verdict.note or '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dayaniklilik kosusunu degerlendirir (F5-039)")
    parser.add_argument("--run", type=Path, default=ROOT / "docs/live/results/endurance.json")
    parser.add_argument(
        "--json", type=Path, default=ROOT / "docs/live/results/endurance-verdict.json"
    )
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args(argv)

    run = cast("dict[str, Any]", json.loads(args.run.read_text(encoding="utf-8")))
    verdicts = evaluate(run)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps([asdict(verdict) for verdict in verdicts], indent=2) + "\n",
        encoding="utf-8",
    )
    if args.markdown is not None:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(run, verdicts), encoding="utf-8")

    for verdict in verdicts:
        print(f"{verdict.name}: {verdict.status} ({verdict.measured})")
    # Sapan bir olcut varsa cikis kodu sifir DEGILDIR: rapor "gecti"
    # gorunurken surecin sessizce devam etmesi istenmez.
    return 0 if all(verdict.status == PASSED for verdict in verdicts) else 1


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
