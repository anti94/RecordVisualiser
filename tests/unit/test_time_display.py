"""İmleç anının üç görünümü — `F3-061`.

Kabul: UTC, yerel ve geçen süre görünümleri **aynı kanonik anı** temsil
eder.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sonar_analyzer.application.time_display import (
    TimeDisplayMode,
    format_elapsed,
    format_instant,
    format_local,
    format_utc,
    next_mode,
)

NS_PER_SECOND = 1_000_000_000

# Kanonik an: 2026-09-10 12:00:12.346 UTC — ns tamsayı aritmetiğiyle kurulur
# (float `.timestamp()` çarpımı bu büyüklükte hassasiyet kaybeder).
INSTANT = datetime(2026, 9, 10, 12, 0, 12, 346_000, tzinfo=timezone.utc)
_INSTANT_WHOLE_S = int(datetime(2026, 9, 10, 12, 0, 12, tzinfo=timezone.utc).timestamp())
INSTANT_NS = _INSTANT_WHOLE_S * NS_PER_SECOND + 346_000_000
# Kayıt 2026-09-10 12:00:00 UTC'de başlıyor -> imleç +12.346 s
START_NS = int(datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc).timestamp()) * NS_PER_SECOND


def test_utc_view_is_the_utc_wall_clock() -> None:
    assert format_utc(INSTANT_NS) == "2026-09-10 12:00:12.346 UTC"


def test_local_view_shifts_by_the_injected_offset() -> None:
    tz = timezone(timedelta(hours=3))
    assert format_local(INSTANT_NS, tz=tz) == "2026-09-10 15:00:12.346 +03:00"


def test_local_view_handles_negative_offsets() -> None:
    tz = timezone(timedelta(hours=-5, minutes=-30))
    assert format_local(INSTANT_NS, tz=tz) == "2026-09-10 06:30:12.346 -05:30"


def test_elapsed_view_is_relative_to_the_recording_start() -> None:
    assert format_elapsed(INSTANT_NS - START_NS) == "t = 12.346 s"


def test_elapsed_before_the_start_is_signed() -> None:
    assert format_elapsed(-1_500_000_000) == "t = -1.500 s"


def test_all_three_views_describe_the_same_instant() -> None:
    tz = timezone(timedelta(hours=2))
    utc = format_instant(INSTANT_NS, TimeDisplayMode.UTC, start_ns=START_NS)
    local = format_instant(INSTANT_NS, TimeDisplayMode.LOCAL, start_ns=START_NS, tz=tz)
    elapsed = format_instant(INSTANT_NS, TimeDisplayMode.ELAPSED, start_ns=START_NS)

    # UTC ve yerel aynı mutlak saniyeyi çözer.
    parsed_utc = datetime.strptime(utc, "%Y-%m-%d %H:%M:%S.%f UTC").replace(tzinfo=timezone.utc)
    parsed_local = datetime.strptime(local, "%Y-%m-%d %H:%M:%S.%f %z")
    assert parsed_utc == parsed_local == INSTANT

    # Geçen süre = mutlak an - kayıt başlangıcı.
    assert elapsed == "t = 12.346 s"
    assert INSTANT_NS - START_NS == 12_346_000_000


def test_format_instant_elapsed_without_start_treats_value_as_elapsed() -> None:
    assert format_instant(5_000_000_000, TimeDisplayMode.ELAPSED) == "t = 5.000 s"


def test_mode_cycle_wraps_around() -> None:
    assert next_mode(TimeDisplayMode.ELAPSED) is TimeDisplayMode.UTC
    assert next_mode(TimeDisplayMode.UTC) is TimeDisplayMode.LOCAL
    assert next_mode(TimeDisplayMode.LOCAL) is TimeDisplayMode.ELAPSED


def test_sub_millisecond_nanoseconds_are_truncated_not_rounded() -> None:
    # 12.346999 s -> hâlâ .346 ms gösterilir (taban bölme).
    assert format_utc(INSTANT_NS + 999_999) == "2026-09-10 12:00:12.346 UTC"
