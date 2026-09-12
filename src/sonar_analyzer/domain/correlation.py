"""Zaman korelasyonu toleransı — plan Bölüm 9.

Sensör örnekleri, BIT sonuçları ve TX geçişleri **aynı ana** düşmez.
Biri 125 ms ızgarasında, diğeri olay anında üretilir; bir olayı bir
örnekle eşlemek her zaman bir **yaklaştırmadır**.

Bu modül o yaklaştırmanın sınırını tanımlar. Sınır olmadan "en yakın
örnek" araması her zaman bir sonuç döndürür — aradaki mesafe bir saat
bile olsa. Uzaktaki bir örneği olayla eşleştirmek, olayı hiç
eşleştirmemekten daha zararlıdır: kullanıcı ilgisiz bir değere bakıp
olayı yorumlar.

Tolerans **yapılandırılabilirdir** (plan Bölüm 9): kayıt periyodu
cihazdan cihaza değişir ve `D-08` (TX START/STOP ilişkilendirme kuralı)
hâlâ açıktır. Sabit bir sayıya gömülü kalsaydı, cevap geldiğinde kodun
içinde aranması gerekirdi.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass

from sonar_analyzer.io.profile_a_format import RECORD_PERIOD_NS

#: Ontanimli tolerans: bir kayit periyodu (125 ms). Bir olay, kendi
#: penceresindeki ornekle eslesir; komsu pencereye tasan eslesme
#: yaklastirmanin sinirini asar.
DEFAULT_TOLERANCE_NS = RECORD_PERIOD_NS


@dataclass(frozen=True)
class CorrelationTolerance:
    """Bir olayın bir örnekle eşleşebileceği en büyük zaman farkı."""

    value_ns: int = DEFAULT_TOLERANCE_NS

    def __post_init__(self) -> None:
        if self.value_ns < 0:
            raise ValueError(f"korelasyon toleransi negatif olamaz: {self.value_ns}")

    def accepts(self, distance_ns: int) -> bool:
        """`distance_ns` tolerans içinde mi (sınır dâhil)."""
        return abs(distance_ns) <= self.value_ns

    def describe(self) -> str:
        """Kullanıcıya gösterilecek biçim: `±125,000 ms`."""
        return f"±{self.value_ns / 1_000_000:,.3f} ms".replace(",", " ")


DEFAULT_TOLERANCE = CorrelationTolerance()


@dataclass(frozen=True)
class NearestMatch:
    """En yakın örneğin konumu, uzaklığı ve tolerans kararı."""

    index: int
    distance_ns: int
    within_tolerance: bool


def nearest_within(
    timestamps_ns: Sequence[int],
    target_ns: int,
    tolerance: CorrelationTolerance = DEFAULT_TOLERANCE,
) -> NearestMatch | None:
    """`target_ns`'e en yakın zaman damgasını bulur.

    `None` yalnız dizi **boşsa** döner. Tolerans dışındaki eşleşme
    atılmaz: hangi örneğin ne kadar uzakta olduğu da bir bilgidir ve
    çağıran taraf bunu kullanıcıya gösterebilir. Karar
    `within_tolerance` alanındadır — sessizce doğru sanılmasın diye
    ayrı taşınır.

    `timestamps_ns` **artan sırada** olmalıdır; ikili arama buna dayanır.
    """
    if not timestamps_ns:
        return None

    position = bisect_left(timestamps_ns, target_ns)
    candidates = [i for i in (position - 1, position) if 0 <= i < len(timestamps_ns)]
    index = min(candidates, key=lambda i: abs(timestamps_ns[i] - target_ns))
    distance = timestamps_ns[index] - target_ns
    return NearestMatch(
        index=index,
        distance_ns=distance,
        within_tolerance=tolerance.accepts(distance),
    )
