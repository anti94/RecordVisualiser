"""Cihaz tick dönüşüm adaptörü — `F2-025`.

`domain.time_base.ticks_to_utc_ns()`'i (`ADR-003-time-base.md` §2.3) parser
tarafına bağlar. Kabul kriteri gereği **ham tick değeri** her zaman sonuçla
birlikte saklanır (`TickConversionResult.raw_ticks`) — dönüşüm sırasında
asla atılmaz; tanılama ve drift analizi ham değere ihtiyaç duyar
(ADR-003 §2.2 "Orijinal cihaz değeri" satırı).

Sarma (wraparound) ve reset ayrımı burada **yok** — bu `F2-026`'nın
kapsamıdır; bu modül yalnızca zaten doğrusal (unwrap edilmiş) bir `ticks`
dizisini UTC ns'ye çevirir.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sonar_analyzer.domain.time_base import TimeBase, ticks_to_utc_ns


@dataclass(frozen=True)
class TickConversionResult:
    """Bir tick değerinin dönüşüm sonucu; ham değer korunur."""

    raw_ticks: int
    timestamp_utc_ns: int
    time_base_id: str


def convert_tick(time_base: TimeBase, ticks: int, ticks0: int) -> TickConversionResult:
    """Ham `ticks`'i UTC ns'ye çevirir; ham değer sonuç içinde saklanır."""
    timestamp_ns = ticks_to_utc_ns(time_base, ticks, ticks0)
    return TickConversionResult(
        raw_ticks=ticks,
        timestamp_utc_ns=timestamp_ns,
        time_base_id=time_base.id,
    )


def convert_ticks_batch(
    time_base: TimeBase, ticks_sequence: Sequence[int], ticks0: int
) -> list[TickConversionResult]:
    """Bir tick dizisini toplu dönüştürür (Profil B kayıt akışı için)."""
    return [convert_tick(time_base, ticks, ticks0) for ticks in ticks_sequence]
