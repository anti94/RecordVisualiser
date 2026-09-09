"""Tanımlı drift düzeltmesini uygulama — `F2-027`.

`docs/adr/ADR-003-time-base.md` §2.6: drift **ölçülür, sessizce
düzeltilmez**. `TimeBase.drift_ppm` sıfırdan farklıysa düzeltme açıkça
uygulanır; ham zaman erişilebilir kalır ve hangi zamanın kullanıldığı
**metadata'da** belirtilir (`DriftCorrectedTimestamp.corrected`) —
düzeltilmiş değer sessizce ham değerin yerine geçmez.

Ölçek örneği (ADR-003 §2.6): 50 ppm sapma 125 ms'te yalnız 6,25 µs, ancak
1 saatte 180 ms'e ulaşır — düzeltmesiz korelasyon uzun kayıtta kayar.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.domain.time_base import TimeBase

#: `drift_ppm` milyonda bir birim tanımlar.
_PPM_DIVISOR = 1_000_000


@dataclass(frozen=True)
class DriftCorrectedTimestamp:
    """Bir zaman değerinin düzeltilmiş ve ham hâli bir arada — düzeltme metadata'da görünür."""

    raw_timestamp_ns: int
    corrected_timestamp_ns: int
    drift_ppm: float
    #: Düzeltme fiilen uygulandı mı (`drift_ppm != 0`); `False` ise ikisi eşittir.
    corrected: bool
    time_base_id: str


def apply_drift_correction(
    time_base: TimeBase, raw_timestamp_ns: int, reference_epoch_ns: int
) -> DriftCorrectedTimestamp:
    """Bilinen `drift_ppm` katsayısıyla düzeltilmiş referans zamanını üretir.

    Düzeltme: `corrected = raw - (raw - reference_epoch_ns) * drift_ppm / 1e6`.
    Sözleşme: pozitif `drift_ppm`, saatin hızlı gittiğini (ölçülen zamanın
    gerçek zamandan ileride olduğunu) temsil eder; düzeltme bu farkı geriye
    doğru çıkarır.

    `drift_ppm == 0` ise düzeltme uygulanmaz (`corrected=False`); ham ve
    düzeltilmiş değer birebir aynı kalır — GPS/PPS disiplinli kaynakta
    (ADR-003 §2.6) veya ölçüm yokken varsayılan budur.
    """
    if time_base.drift_ppm == 0.0:
        return DriftCorrectedTimestamp(
            raw_timestamp_ns=raw_timestamp_ns,
            corrected_timestamp_ns=raw_timestamp_ns,
            drift_ppm=0.0,
            corrected=False,
            time_base_id=time_base.id,
        )

    elapsed_ns = raw_timestamp_ns - reference_epoch_ns
    correction_ns = round(elapsed_ns * time_base.drift_ppm / _PPM_DIVISOR)
    return DriftCorrectedTimestamp(
        raw_timestamp_ns=raw_timestamp_ns,
        corrected_timestamp_ns=raw_timestamp_ns - correction_ns,
        drift_ppm=time_base.drift_ppm,
        corrected=True,
        time_base_id=time_base.id,
    )
