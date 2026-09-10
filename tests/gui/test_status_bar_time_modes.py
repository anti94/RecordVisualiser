"""Durum çubuğu imleç zamanı: UTC / yerel / geçen süre — `F3-061`.

Kabul: üç görünüm aynı kanonik anı temsil eder; alana tıklamak
görünümü döndürür.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.time_display import TimeDisplayMode
from sonar_analyzer.ui.status_bar import EMPTY_VALUE, AppStatusBar

pytestmark = pytest.mark.gui

NS_PER_SECOND = 1_000_000_000
START = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
START_NS = int(START.timestamp() * NS_PER_SECOND)


@pytest.fixture()
def bar(qtbot: QtBot) -> AppStatusBar:
    widget = AppStatusBar()
    qtbot.addWidget(widget)
    return widget


def test_default_mode_is_elapsed_and_keeps_the_legacy_format(bar: AppStatusBar) -> None:
    bar.set_time_origin(START_NS)
    bar.set_cursor_time(12.3456)

    assert bar.cursor_time_mode is TimeDisplayMode.ELAPSED
    assert bar.field_value("cursor") == "t = 12.346 s"


def test_clicking_the_cursor_field_cycles_the_view(bar: AppStatusBar) -> None:
    bar.set_time_origin(START_NS)
    bar.set_cursor_time(12.346)

    bar.cursor_time_label.clicked.emit()  # elapsed -> UTC
    assert bar.cursor_time_mode is TimeDisplayMode.UTC
    assert bar.field_value("cursor") == "2026-09-10 12:00:12.346 UTC"

    bar.cursor_time_label.clicked.emit()  # UTC -> local
    assert bar.cursor_time_mode is TimeDisplayMode.LOCAL

    bar.cursor_time_label.clicked.emit()  # local -> elapsed
    assert bar.cursor_time_mode is TimeDisplayMode.ELAPSED
    assert bar.field_value("cursor") == "t = 12.346 s"


def test_utc_and_elapsed_views_agree_on_the_instant(bar: AppStatusBar) -> None:
    bar.set_time_origin(START_NS)
    bar.set_cursor_time(12.346)

    bar.cycle_cursor_time_mode()  # -> UTC
    utc_text = bar.field_value("cursor")
    parsed = datetime.strptime(utc_text, "%Y-%m-%d %H:%M:%S.%f UTC").replace(tzinfo=timezone.utc)

    # UTC metni = kayıt başlangıcı (12:00:00) + geçen süre (12.346 s).
    assert parsed == datetime(2026, 9, 10, 12, 0, 12, 346_000, tzinfo=timezone.utc)
    assert START_NS + 12_346_000_000 == 1_789_041_612_346_000_000


def test_cycle_emits_the_new_mode(bar: AppStatusBar) -> None:
    seen: list[TimeDisplayMode] = []
    bar.cursor_time_mode_changed.connect(seen.append)

    bar.cycle_cursor_time_mode()
    bar.cycle_cursor_time_mode()

    assert seen == [TimeDisplayMode.UTC, TimeDisplayMode.LOCAL]


def test_without_an_origin_absolute_modes_fall_back_to_elapsed(bar: AppStatusBar) -> None:
    bar.set_cursor_time(3.0)
    bar.cycle_cursor_time_mode()  # UTC istendi ama köken yok

    assert bar.cursor_time_mode is TimeDisplayMode.UTC
    assert bar.field_value("cursor") == "t = 3.000 s"


def test_clearing_the_cursor_blanks_the_field_in_every_mode(bar: AppStatusBar) -> None:
    bar.set_time_origin(START_NS)
    bar.set_cursor_time(5.0)
    bar.cycle_cursor_time_mode()  # UTC

    bar.set_cursor_time(None)

    assert bar.field_value("cursor") == EMPTY_VALUE
