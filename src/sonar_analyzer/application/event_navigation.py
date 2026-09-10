"""Zamana ve komşu olaya gitme yardımcıları — `F3-059`.

Saf Python: Qt yok, `GUI olmadan` doğrulanır.

* ``clamp_time_ns`` — sınır dışı bir hedef zamanı `[start_ns, end_ns]`
  aralığına **güvenle** kenetler (ters aralık da düzeltilir).
* ``previous_event`` / ``next_event`` — verilen ana göre kesin olarak
  önceki / sonraki olayı döndürür. Olaylar kronolojik sıraya göre
  değerlendirilir; giriş sırasız olsa bile sonuç **zaman sırasını korur**.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Sequence

from sonar_analyzer.domain.event import Event


def clamp_time_ns(target_ns: int, start_ns: int, end_ns: int) -> int:
    """`target_ns`'i `[start_ns, end_ns]` aralığına kenetler.

    `end_ns < start_ns` verilirse uçlar takas edilir, böylece çağıran
    yanlış sıralı bir aralıkla da güvenli bir sonuç alır.
    """
    low, high = (start_ns, end_ns) if start_ns <= end_ns else (end_ns, start_ns)
    if target_ns < low:
        return low
    if target_ns > high:
        return high
    return target_ns


def _sorted_by_time(events: Sequence[Event]) -> list[Event]:
    return sorted(events, key=lambda event: event.timestamp_ns)


def previous_event(events: Sequence[Event], reference_ns: int) -> Event | None:
    """`reference_ns`'ten **kesin olarak önce** gelen son olay; yoksa ``None``."""
    ordered = _sorted_by_time(events)
    times = [event.timestamp_ns for event in ordered]
    index = bisect_left(times, reference_ns)
    if index == 0:
        return None
    return ordered[index - 1]


def next_event(events: Sequence[Event], reference_ns: int) -> Event | None:
    """`reference_ns`'ten **kesin olarak sonra** gelen ilk olay; yoksa ``None``."""
    ordered = _sorted_by_time(events)
    times = [event.timestamp_ns for event in ordered]
    index = bisect_right(times, reference_ns)
    if index >= len(ordered):
        return None
    return ordered[index]
