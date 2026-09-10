"""İmleç anını üç görünümde biçimleyen yardımcılar — `F3-061`.

Saf Python: Qt yok, `GUI olmadan` doğrulanır. Kanonik an her zaman
`int64` UTC epoch **nanosaniye**'dir (ADR-003). Üç görünüm aynı anı
temsil eder; yalnız sunum değişir:

* ``ELAPSED`` — kayıt başlangıcından bu yana geçen süre (``t = 12.346 s``).
* ``UTC``     — UTC duvar saati (``2026-09-10 12:00:12.346 UTC``).
* ``LOCAL``   — yerel duvar saati + UTC ofseti
  (``2026-09-10 15:00:12.346 +03:00``).

Yerel görünüm için saat dilimi enjekte edilebilir; verilmezse sistem
yereli kullanılır (testlerde sabit bir ``timezone`` verilir).
"""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from enum import Enum

from sonar_analyzer.domain.time_range import NS_PER_SECOND

_NS_PER_MS = 1_000_000


class TimeDisplayMode(str, Enum):
    """İmleç zamanı gösterim kipi."""

    ELAPSED = "elapsed"
    UTC = "utc"
    LOCAL = "local"


#: Döngü sırası — kullanıcı alana tıkladıkça bu sırayla ilerler.
MODE_CYCLE: tuple[TimeDisplayMode, ...] = (
    TimeDisplayMode.ELAPSED,
    TimeDisplayMode.UTC,
    TimeDisplayMode.LOCAL,
)

#: Kısa etiket (ipucu / rozetler için).
MODE_LABEL: dict[TimeDisplayMode, str] = {
    TimeDisplayMode.ELAPSED: "Elapsed",
    TimeDisplayMode.UTC: "UTC",
    TimeDisplayMode.LOCAL: "Local",
}


def next_mode(mode: TimeDisplayMode) -> TimeDisplayMode:
    """Döngüdeki bir sonraki kip (``LOCAL`` -> ``ELAPSED``)."""
    index = MODE_CYCLE.index(mode)
    return MODE_CYCLE[(index + 1) % len(MODE_CYCLE)]


def format_elapsed(elapsed_ns: int) -> str:
    """Kayıt başından bu yana geçen süre — ``t = 12.346 s``.

    Negatif değer (imleç kayıt başından önce) işaretiyle gösterilir.
    """
    seconds = elapsed_ns / NS_PER_SECOND
    return f"t = {seconds:.3f} s"


def _split(timestamp_ns: int) -> tuple[int, int]:
    """`(tam_saniye, kalan_milisaniye)` — taban bölme, negatifte de tutarlı."""
    whole_s, rem_ns = divmod(timestamp_ns, NS_PER_SECOND)
    return whole_s, rem_ns // _NS_PER_MS


def format_utc(timestamp_ns: int) -> str:
    """UTC duvar saati — ``2026-09-10 12:00:12.346 UTC``."""
    whole_s, ms = _split(timestamp_ns)
    moment = datetime.fromtimestamp(whole_s, tz=timezone.utc)
    return f"{moment:%Y-%m-%d %H:%M:%S}.{ms:03d} UTC"


def format_local(timestamp_ns: int, *, tz: tzinfo | None = None) -> str:
    """Yerel duvar saati + ofset — ``2026-09-10 15:00:12.346 +03:00``.

    `tz` verilmezse sistem yereli kullanılır.
    """
    whole_s, ms = _split(timestamp_ns)
    moment = datetime.fromtimestamp(whole_s, tz=timezone.utc).astimezone(tz)
    raw_offset = moment.strftime("%z") or "+0000"
    offset = f"{raw_offset[:3]}:{raw_offset[3:]}"
    return f"{moment:%Y-%m-%d %H:%M:%S}.{ms:03d} {offset}"


def format_instant(
    timestamp_ns: int,
    mode: TimeDisplayMode,
    *,
    start_ns: int | None = None,
    tz: tzinfo | None = None,
) -> str:
    """`timestamp_ns` kanonik anını `mode`'a göre biçimler.

    ``ELAPSED`` için `start_ns` gerekir; verilmemişse ``0`` varsayılır
    (mutlak an geçen süre gibi gösterilir).
    """
    if mode is TimeDisplayMode.ELAPSED:
        return format_elapsed(timestamp_ns - (start_ns or 0))
    if mode is TimeDisplayMode.UTC:
        return format_utc(timestamp_ns)
    return format_local(timestamp_ns, tz=tz)
