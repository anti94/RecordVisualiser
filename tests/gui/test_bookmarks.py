"""Bookmark ekleme, düzenleme ve silme — `F4-075`.

Kabul: işaret timeline'da görünür; seçim ilgili zamana gider.

"Timeline'da görünür": eklenen her işaret grafikte bir çizgi (nokta) ya
da bant (aralık) olur ve zamanı X ekseniyle eşleşir. "Seçim ilgili zamana
gider": listede bir satır seçmek hem oynatma imlecini hem de grafiğin
görünür penceresini o zamana taşır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.annotation import Annotation, AnnotationSet
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.docks.bookmark_panel import (
    COLUMNS,
    EMPTY_HINT,
    POINT_DURATION,
    BookmarkPanel,
    format_duration,
    format_offset,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

SECOND = 1_000_000_000
DURATION_S = 10.0


@pytest.fixture()
def panel(qtbot: QtBot) -> BookmarkPanel:
    widget = BookmarkPanel()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=DURATION_S, sample_rate_hz=50.0))
    window.open_channel("ch0")
    return window


def _start_ns(win: MainWindow) -> int:
    repository = win.repository
    assert repository is not None
    return repository.metadata().time_range.start_ns


def _add(win: MainWindow, label: str, text: str = "") -> str:
    """Panel üzerinden bir işaret ekler ve kimliğini döndürür."""
    panel = win.bottom_dock.bookmarks
    panel.label_input.setText(label)
    panel.text_input.setText(text)
    panel.add_button.click()
    added = [item for item in win.annotations if item.label == label]
    assert len(added) == 1
    return added[0].id


# --------------------------------------------------------------------------- #
# panel bicimi
# --------------------------------------------------------------------------- #


def test_an_empty_panel_shows_a_hint_and_no_rows(panel: BookmarkPanel) -> None:
    assert panel.row_count() == 0
    assert panel.hint.text() == EMPTY_HINT
    assert panel.selected_id() == ""


def test_the_columns_are_time_duration_label_and_text(panel: BookmarkPanel) -> None:
    assert COLUMNS == ("Zaman", "Süre", "Etiket", "Not")
    assert panel.table.columnCount() == 4


def test_a_point_row_shows_no_duration(panel: BookmarkPanel) -> None:
    marks = AnnotationSet((Annotation.bookmark("TX", 3 * SECOND, annotation_id="b1"),))
    panel.set_annotations(marks)
    assert panel.row_texts(0) == ["3.000 s", POINT_DURATION, "TX", ""]


def test_a_range_row_shows_its_duration(panel: BookmarkPanel) -> None:
    marks = AnnotationSet(
        (Annotation(id="r1", label="Gürültü", start_ns=2 * SECOND, end_ns=5 * SECOND, text="not"),)
    )
    panel.set_annotations(marks)
    assert panel.row_texts(0) == ["2.000 s", "3.000 s", "Gürültü", "not"]


def test_times_are_shown_relative_to_the_recording_start(panel: BookmarkPanel) -> None:
    base = 1_788_901_200_000_000_000
    marks = AnnotationSet((Annotation.bookmark("x", base + 4 * SECOND, annotation_id="b1"),))
    panel.set_annotations(marks, start_ns=base)
    assert panel.row_texts(0)[0] == "4.000 s"


def test_multiline_notes_stay_on_one_row(panel: BookmarkPanel) -> None:
    marks = AnnotationSet(
        (Annotation.bookmark("x", SECOND, text="ilk\nikinci", annotation_id="b1"),)
    )
    panel.set_annotations(marks)
    assert "\n" not in panel.row_texts(0)[3]
    assert "ilk" in panel.row_texts(0)[3] and "ikinci" in panel.row_texts(0)[3]


def test_the_formatters_are_readable() -> None:
    assert format_offset(1_500_000_000) == "1.500 s"
    assert format_duration(0) == POINT_DURATION
    assert format_duration(2 * SECOND) == "2.000 s"


def test_rows_follow_the_time_order(panel: BookmarkPanel) -> None:
    marks = AnnotationSet(
        (
            Annotation.bookmark("geç", 5 * SECOND, annotation_id="b2"),
            Annotation.bookmark("erken", SECOND, annotation_id="b1"),
        )
    )
    panel.set_annotations(marks)
    assert [panel.row_texts(row)[2] for row in range(panel.row_count())] == ["erken", "geç"]


# --------------------------------------------------------------------------- #
# dugme kurallari
# --------------------------------------------------------------------------- #


def test_adding_needs_a_label(panel: BookmarkPanel) -> None:
    assert not panel.add_button.isEnabled()
    panel.label_input.setText("TX")
    assert panel.add_button.isEnabled()
    panel.label_input.setText("   ")
    assert not panel.add_button.isEnabled()


def test_editing_and_removing_need_a_selection(panel: BookmarkPanel) -> None:
    panel.set_annotations(AnnotationSet((Annotation.bookmark("x", SECOND, annotation_id="b1"),)))
    assert not panel.edit_button.isEnabled()
    assert not panel.remove_button.isEnabled()
    panel.select("b1")
    assert panel.edit_button.isEnabled()
    assert panel.remove_button.isEnabled()


def test_selecting_a_row_loads_its_fields(panel: BookmarkPanel) -> None:
    marks = AnnotationSet((Annotation.bookmark("TX", SECOND, text="not", annotation_id="b1"),))
    panel.set_annotations(marks)
    panel.select("b1")
    assert panel.label_input.text() == "TX"
    assert panel.text_input.text() == "not"


def test_an_invalid_add_emits_nothing(panel: BookmarkPanel) -> None:
    seen: list[tuple[str, str]] = []

    def record(label: str, text: str) -> None:
        seen.append((label, text))

    panel.add_requested.connect(record)
    panel.label_input.setText("  ")
    panel.add_button.click()
    assert seen == []


def test_the_selection_survives_a_refresh(panel: BookmarkPanel) -> None:
    marks = AnnotationSet(
        (
            Annotation.bookmark("a", SECOND, annotation_id="b1"),
            Annotation.bookmark("b", 2 * SECOND, annotation_id="b2"),
        )
    )
    panel.set_annotations(marks)
    panel.select("b2")
    panel.set_annotations(marks.added(Annotation.bookmark("c", 3 * SECOND, annotation_id="b3")))
    assert panel.selected_id() == "b2"


# --------------------------------------------------------------------------- #
# ekleme: isaret timeline'da GORUNUR
# --------------------------------------------------------------------------- #


def test_a_new_recording_starts_with_no_marks(win: MainWindow) -> None:
    assert len(win.annotations) == 0
    assert win.plot_panel.bookmark_count() == 0


def test_adding_a_bookmark_puts_it_on_the_timeline(win: MainWindow) -> None:
    win.playback_dock.set_position(4.0)
    _add(win, "TX başlangıcı")

    assert len(win.annotations) == 1
    assert win.plot_panel.bookmark_count() == 1
    assert win.plot_panel.bookmark_times_ns() == [_start_ns(win) + 4 * SECOND]


def test_the_mark_time_matches_the_plot_x_axis(win: MainWindow) -> None:
    """İşaretin zamanı grafik X koordinatıyla eşleşir."""
    win.playback_dock.set_position(6.0)
    _add(win, "Nokta")

    timestamp = win.plot_panel.bookmark_times_ns()[0]
    assert win.plot_panel.timestamp_ns_for_x(win.plot_panel.x_for_timestamp_ns(timestamp)) == (
        timestamp
    )


def test_a_selected_region_becomes_a_range_mark(win: MainWindow) -> None:
    win.plot_panel.set_time_region(2.0, 5.0)
    _add(win, "Gürültü")

    mark = next(iter(win.annotations))
    assert mark.is_range
    assert abs(mark.duration_ns - 3 * SECOND) < SECOND // 100
    assert win.plot_panel.bookmark_count() == 1


def test_without_a_region_the_mark_is_a_point(win: MainWindow) -> None:
    win.playback_dock.set_position(1.0)
    _add(win, "An")
    assert next(iter(win.annotations)).is_point


def test_the_note_is_kept(win: MainWindow) -> None:
    _add(win, "Etiket", "uzun bir not")
    assert next(iter(win.annotations)).text == "uzun bir not"


def test_adding_is_logged(win: MainWindow) -> None:
    _add(win, "TX")
    assert any("İşaret eklendi" in line for line in win.bottom_dock.log_lines())


def test_several_marks_all_appear(win: MainWindow) -> None:
    win.playback_dock.set_position(1.0)
    _add(win, "bir")
    win.playback_dock.set_position(3.0)
    _add(win, "iki")
    assert len(win.annotations) == 2
    assert win.plot_panel.bookmark_count() == 2
    assert win.bottom_dock.bookmarks.row_count() == 2


# --------------------------------------------------------------------------- #
# duzenleme
# --------------------------------------------------------------------------- #


def test_editing_changes_the_label_without_moving_the_mark(win: MainWindow) -> None:
    win.playback_dock.set_position(2.0)
    mark_id = _add(win, "Eski")
    before = next(iter(win.annotations)).start_ns

    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.label_input.setText("Yeni")
    panel.edit_button.click()

    mark = win.annotations.get(mark_id)
    assert mark is not None
    assert mark.label == "Yeni"
    assert mark.start_ns == before
    assert len(win.annotations) == 1


def test_editing_changes_the_note(win: MainWindow) -> None:
    mark_id = _add(win, "Etiket", "ilk not")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.text_input.setText("düzeltilmiş not")
    panel.edit_button.click()

    mark = win.annotations.get(mark_id)
    assert mark is not None and mark.text == "düzeltilmiş not"


def test_the_edited_label_appears_on_the_timeline_row(win: MainWindow) -> None:
    mark_id = _add(win, "Eski")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.label_input.setText("Yeni")
    panel.edit_button.click()
    assert panel.row_texts(0)[2] == "Yeni"


def test_editing_is_logged(win: MainWindow) -> None:
    mark_id = _add(win, "Eski")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.label_input.setText("Yeni")
    panel.edit_button.click()
    assert any("İşaret güncellendi" in line for line in win.bottom_dock.log_lines())


# --------------------------------------------------------------------------- #
# silme
# --------------------------------------------------------------------------- #


def test_removing_takes_the_mark_off_the_timeline(win: MainWindow) -> None:
    mark_id = _add(win, "Silinecek")
    assert win.plot_panel.bookmark_count() == 1

    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.remove_button.click()

    assert len(win.annotations) == 0
    assert win.plot_panel.bookmark_count() == 0
    assert panel.row_count() == 0


def test_removing_one_leaves_the_others(win: MainWindow) -> None:
    win.playback_dock.set_position(1.0)
    first = _add(win, "bir")
    win.playback_dock.set_position(3.0)
    _add(win, "iki")

    panel = win.bottom_dock.bookmarks
    panel.select(first)
    panel.remove_button.click()

    assert [item.label for item in win.annotations] == ["iki"]
    assert win.plot_panel.bookmark_count() == 1


def test_removing_is_logged(win: MainWindow) -> None:
    mark_id = _add(win, "Silinecek")
    panel = win.bottom_dock.bookmarks
    panel.select(mark_id)
    panel.remove_button.click()
    assert any("İşaret silindi" in line for line in win.bottom_dock.log_lines())


# --------------------------------------------------------------------------- #
# secim ILGILI ZAMANA gider
# --------------------------------------------------------------------------- #


def test_selecting_a_mark_moves_the_playhead(win: MainWindow) -> None:
    win.playback_dock.set_position(7.0)
    mark_id = _add(win, "Uzak")
    win.playback_dock.set_position(0.0)
    assert abs(win.playback_dock.position_s) < 0.05

    win.bottom_dock.bookmarks.clear_selection()
    win.bottom_dock.bookmarks.select(mark_id)

    assert abs(win.playback_dock.position_s - 7.0) < 0.05


def test_selecting_a_mark_centres_the_plot_on_its_time(win: MainWindow) -> None:
    win.playback_dock.set_position(8.0)
    mark_id = _add(win, "Uzak")
    win.plot_panel.set_x_range(0.0, 1.0)

    win.bottom_dock.bookmarks.clear_selection()
    win.bottom_dock.bookmarks.select(mark_id)

    target_x = win.plot_panel.x_for_timestamp_ns(_start_ns(win) + 8 * SECOND)
    x_min, x_max = win.plot_panel.visible_x_range()
    assert x_min <= target_x <= x_max


def test_selecting_a_range_mark_goes_to_its_start(win: MainWindow) -> None:
    win.plot_panel.set_time_region(3.0, 6.0)
    mark_id = _add(win, "Aralık")
    win.playback_dock.set_position(0.0)

    win.bottom_dock.bookmarks.clear_selection()
    win.bottom_dock.bookmarks.select(mark_id)

    mark = win.annotations.get(mark_id)
    assert mark is not None
    expected_s = (mark.start_ns - _start_ns(win)) / SECOND
    assert abs(win.playback_dock.position_s - expected_s) < 0.05


def test_clearing_the_selection_does_not_navigate(win: MainWindow) -> None:
    win.playback_dock.set_position(5.0)
    _add(win, "x")
    win.playback_dock.set_position(1.0)
    win.bottom_dock.bookmarks.clear_selection()
    assert abs(win.playback_dock.position_s - 1.0) < 0.05


# --------------------------------------------------------------------------- #
# kayit degisince
# --------------------------------------------------------------------------- #


def test_opening_another_recording_clears_the_marks(win: MainWindow) -> None:
    _add(win, "Eski kayıt")
    win.set_repository(MockRecordingRepository(duration_s=3.0))
    assert len(win.annotations) == 0
    assert win.bottom_dock.bookmarks.row_count() == 0
    assert win.plot_panel.bookmark_count() == 0
