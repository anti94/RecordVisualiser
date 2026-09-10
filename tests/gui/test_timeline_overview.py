"""Kayıt geneli Timeline özeti — `F3-054`.

Kabul: başlangıç, bitiş ve olay yoğunluğu doğru konumlanır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.ui.docks.timeline_overview import TimelineOverview

pytestmark = pytest.mark.gui

START = 1_000_000_000_000
END = START + 10_000_000_000  # 10 s pencere


def _ev(t_offset_s: float) -> Event:
    return Event(
        timestamp_ns=START + int(t_offset_s * 1_000_000_000),
        source="BIT",
        category="BIT",
        severity=Severity.WARNING,
        code="X",
        message="e",
    )


@pytest.fixture()
def timeline(qtbot: QtBot) -> TimelineOverview:
    widget = TimelineOverview()
    qtbot.addWidget(widget)
    widget.resize(600, 30)
    widget.set_recording(TimeRange(START, END))
    return widget


# -- baslangic / bitis konumu ------------------------------


def test_start_maps_to_zero_and_end_maps_to_one(timeline: TimelineOverview) -> None:
    assert timeline.start_ns == START
    assert timeline.end_ns == END
    assert timeline.x_fraction_for_ns(START) == 0.0
    assert timeline.x_fraction_for_ns(END) == 1.0


def test_midpoint_maps_to_one_half(timeline: TimelineOverview) -> None:
    assert timeline.x_fraction_for_ns(START + 5_000_000_000) == 0.5
    assert timeline.x_fraction_for_ns(START + 2_500_000_000) == 0.25


def test_out_of_range_times_clamp_to_the_ends(timeline: TimelineOverview) -> None:
    assert timeline.x_fraction_for_ns(START - 9_000_000_000) == 0.0
    assert timeline.x_fraction_for_ns(END + 9_000_000_000) == 1.0


def test_mapping_without_a_recording_raises(qtbot: QtBot) -> None:
    bare = TimelineOverview()
    qtbot.addWidget(bare)
    with pytest.raises(RuntimeError):
        bare.x_fraction_for_ns(START)


# -- olay yogunlugu ------------------------------------


def test_event_density_counts_events_per_bucket(timeline: TimelineOverview) -> None:
    # 10 s / 10 kova -> her kova 1 s. İlk saniyeye 3, altıncıya 1.
    timeline.set_events([_ev(0.1), _ev(0.4), _ev(0.9), _ev(5.5)])

    density = timeline.event_density(buckets=10)
    assert sum(density) == 4
    assert density[0] == 3
    assert density[5] == 1
    assert density[9] == 0


def test_event_exactly_at_the_end_lands_in_the_last_bucket(timeline: TimelineOverview) -> None:
    timeline.set_events([_ev(10.0)])  # tam bitiş

    density = timeline.event_density(buckets=10)
    assert density[-1] == 1
    assert sum(density) == 1


def test_density_is_empty_without_events(timeline: TimelineOverview) -> None:
    assert timeline.event_density(buckets=8) == [0] * 8
    assert timeline.event_count() == 0


def test_density_before_a_recording_is_all_zero(qtbot: QtBot) -> None:
    bare = TimelineOverview()
    qtbot.addWidget(bare)
    bare.set_events([_ev(1.0)])

    assert bare.event_density(buckets=4) == [0, 0, 0, 0]


def test_non_positive_bucket_count_raises(timeline: TimelineOverview) -> None:
    with pytest.raises(ValueError, match="pozitif"):
        timeline.event_density(buckets=0)


def test_clear_resets_range_and_events(timeline: TimelineOverview) -> None:
    timeline.set_events([_ev(1.0), _ev(2.0)])

    timeline.clear()

    assert timeline.start_ns is None
    assert timeline.event_count() == 0


def test_painting_a_populated_timeline_does_not_crash(timeline: TimelineOverview) -> None:
    timeline.set_events([_ev(0.5), _ev(0.6), _ev(9.9)])
    timeline.show()
    timeline.repaint()  # paintEvent yolu

    assert timeline.event_count() == 3
