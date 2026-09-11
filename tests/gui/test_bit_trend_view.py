"""BIT / Status trend görünümü — `F4-081`.

Kabul: sağ özet ile ayrıntılı trend aynı durumu gösterir.

Bu eşitlik tesadüfe bırakılmaz: iki yüzey de `BitState.severity_rank`
sıralamasını ve `bit_style()` etiketini kullanır. Test her alt sistem için
iki metni **karşılaştırır**, ayrıca durumun ayrıştığı bir kurulum kurup
(aynı bileşende PASS ve FAIL) ikisinin de "Fail" dediğini gösterir.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import BitResult, BitState
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.panels.bit_trend_view import (
    COLUMNS,
    EMPTY_HINT,
    NO_FAILURE,
    BitTrendView,
    format_ratio,
    format_seconds,
    worst_state,
)
from sonar_analyzer.ui.status_icons import bit_style
from sonar_analyzer.ui.view_tab_bar import ENABLED_TABS

pytestmark = pytest.mark.gui

S = 1_000_000_000
THERMAL = "Thermal Management"
POWER = "Power"


@pytest.fixture()
def view(qtbot: QtBot) -> BitTrendView:
    widget = BitTrendView()
    qtbot.addWidget(widget)
    return widget


def _runs(states: str, *, component: str = THERMAL, test_id: int = 3) -> list[BitResult]:
    mapping = {"P": BitState.PASS, "F": BitState.FAIL, "W": BitState.WARN}
    return [
        BitResult(
            timestamp_ns=index * S, test_id=test_id, component=component, state=mapping[letter]
        )
        for index, letter in enumerate(states)
    ]


# --------------------------------------------------------------------------- #
# gorunum bicimi
# --------------------------------------------------------------------------- #


def test_an_empty_view_shows_a_hint(view: BitTrendView) -> None:
    assert view.row_count() == 0
    assert view.hint.text() == EMPTY_HINT


def test_the_columns_cover_state_changes_and_duration() -> None:
    assert COLUMNS == ("Subsystem", "Durum", "Değişim", "Arıza süresi", "Arıza oranı", "İlk arıza")


def test_a_known_sequence_fills_the_row(view: BitTrendView) -> None:
    """`PPFFFP` + 8 s: iki değişim, 3 s arıza, %37.5, ilk arıza 2 s."""
    view.set_results(_runs("PPFFFP"), end_ns=8 * S)

    assert view.subsystem_names() == [THERMAL]
    assert view.cell(THERMAL, "Durum") == "Fail"
    assert view.cell(THERMAL, "Değişim") == "2"
    assert view.cell(THERMAL, "Arıza süresi") == "3.000 s"
    assert view.cell(THERMAL, "Arıza oranı") == "%37.5"
    assert view.cell(THERMAL, "İlk arıza") == "2.000 s"


def test_a_clean_subsystem_reports_no_failure(view: BitTrendView) -> None:
    view.set_results(_runs("PPPP"), end_ns=6 * S)
    assert view.cell(THERMAL, "Durum") == "OK"
    assert view.cell(THERMAL, "Arıza süresi") == "0.000 s"
    assert view.cell(THERMAL, "Arıza oranı") == "%0.0"
    assert view.cell(THERMAL, "İlk arıza") == NO_FAILURE


def test_times_are_relative_to_the_recording_start(view: BitTrendView) -> None:
    base = 1_788_901_200_000_000_000
    runs = [
        BitResult(timestamp_ns=base + index * S, test_id=3, component=THERMAL, state=state)
        for index, state in enumerate([BitState.PASS, BitState.FAIL])
    ]
    view.set_results(runs, start_ns=base, end_ns=base + 4 * S)
    assert view.cell(THERMAL, "İlk arıza") == "1.000 s"


def test_subsystems_are_listed_alphabetically(view: BitTrendView) -> None:
    view.set_results([*_runs("PF", component=POWER, test_id=9), *_runs("PP")], end_ns=4 * S)
    assert view.subsystem_names() == [POWER, THERMAL]


def test_clearing_empties_the_table(view: BitTrendView) -> None:
    view.set_results(_runs("PF"), end_ns=4 * S)
    view.clear()
    assert view.row_count() == 0
    assert view.trends() == ()


def test_an_unknown_column_is_refused(view: BitTrendView) -> None:
    view.set_results(_runs("PF"), end_ns=4 * S)
    with pytest.raises(KeyError, match="Tanımsız trend sütunu"):
        view.cell(THERMAL, "Yok")


def test_an_unknown_subsystem_is_refused(view: BitTrendView) -> None:
    view.set_results(_runs("PF"), end_ns=4 * S)
    with pytest.raises(KeyError, match="Trend tablosunda yok"):
        view.cell("Hic yok", "Durum")


def test_the_formatters_are_readable() -> None:
    assert format_seconds(1_500_000_000) == "1.500 s"
    assert format_ratio(0.375) == "%37.5"


# --------------------------------------------------------------------------- #
# en kotu durum olcutu
# --------------------------------------------------------------------------- #


def test_the_worst_state_of_an_empty_trend_is_none() -> None:
    from sonar_analyzer.analysis.bit_trend import build_trend

    assert worst_state(build_trend([])) is None


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        ("PPP", BitState.PASS),
        ("PWP", BitState.WARN),
        ("PFP", BitState.FAIL),
        ("PWF", BitState.FAIL),
        ("FWP", BitState.FAIL),
    ],
)
def test_the_worst_state_wins_regardless_of_order(
    view: BitTrendView, states: str, expected: BitState
) -> None:
    """Geçmiş bir arıza, sonradan PASS olsa da gizlenmez."""
    view.set_results(_runs(states), end_ns=len(states) * S + S)
    assert view.cell(THERMAL, "Durum") == bit_style(expected).label


# --------------------------------------------------------------------------- #
# OZET ile TREND AYNI DURUMU gosterir
# --------------------------------------------------------------------------- #


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=10.0))
    return window


def test_the_bit_status_tab_is_enabled() -> None:
    assert "BIT / Status" in ENABLED_TABS


def test_selecting_the_tab_shows_the_trend_view(win: MainWindow) -> None:
    titles = win.view_tabs.tab_titles()
    win.view_tabs.setCurrentIndex(titles.index("BIT / Status"))
    assert win.center_stack.currentWidget() is win.bit_trend_view
    assert not win.center_shows_plot


def test_both_surfaces_list_the_same_subsystems(win: MainWindow) -> None:
    summary = win.right_dock.bit_status.subsystem_names()
    assert summary
    assert sorted(win.bit_trend_view.subsystem_names()) == sorted(summary)


def test_every_subsystem_shows_the_same_state_on_both_surfaces(win: MainWindow) -> None:
    """Kabul kriterinin kendisi."""
    for component in win.right_dock.bit_status.subsystem_names():
        assert win.bit_trend_view.status_text(component) == win.right_dock.bit_status.status_text(
            component
        )


def test_a_subsystem_that_recovered_still_reads_fail_on_both(qtbot: QtBot, win: MainWindow) -> None:
    """Aynı bileşende önce FAIL sonra PASS: iki yüzey de en kötüyü gösterir."""
    runs = _runs("PFP")
    win.right_dock.bit_status.set_results(runs)
    win.bit_trend_view.set_results(runs, end_ns=5 * S)

    assert win.right_dock.bit_status.status_text(THERMAL) == "Fail"
    assert win.bit_trend_view.status_text(THERMAL) == "Fail"


def test_a_warning_is_not_softened_on_either_surface(win: MainWindow) -> None:
    runs = _runs("PWP")
    win.right_dock.bit_status.set_results(runs)
    win.bit_trend_view.set_results(runs, end_ns=5 * S)

    assert win.right_dock.bit_status.status_text(THERMAL) == "Warning"
    assert win.bit_trend_view.status_text(THERMAL) == "Warning"


def test_the_overall_badge_agrees_with_the_worst_trend_row(win: MainWindow) -> None:
    overall = win.right_dock.bit_status.overall_state()
    assert overall is not None
    worst_label = max(
        (win.bit_trend_view.status_text(name) for name in win.bit_trend_view.subsystem_names()),
        key=lambda label: _label_rank(label),
    )
    assert worst_label == bit_style(overall).label


def _label_rank(label: str) -> int:
    for state in BitState:
        if bit_style(state).label == label:
            return state.severity_rank
    return 0


def test_opening_another_recording_refreshes_both_surfaces(win: MainWindow) -> None:
    """İki yüzey birlikte temizlenir ve birlikte yeniden dolar."""
    assert win.bit_trend_view.row_count() > 0

    win.set_repository(MockRecordingRepository(duration_s=4.0, seed=7))

    assert win.bit_trend_view.row_count() > 0
    assert sorted(win.bit_trend_view.subsystem_names()) == sorted(
        win.right_dock.bit_status.subsystem_names()
    )
    for component in win.right_dock.bit_status.subsystem_names():
        assert win.bit_trend_view.status_text(component) == win.right_dock.bit_status.status_text(
            component
        )


def test_a_recording_without_bit_data_empties_both_surfaces(win: MainWindow) -> None:
    win.set_recording(win.repository.metadata(), win.repository.channels())  # type: ignore[union-attr]
    assert win.bit_trend_view.row_count() == 0
    assert win.right_dock.bit_status.row_count() == 0


def test_the_trend_adds_time_that_the_summary_does_not_have(win: MainWindow) -> None:
    """Trend özetin yerine geçmez; üstüne zaman boyutunu ekler."""
    for component in win.bit_trend_view.subsystem_names():
        assert win.bit_trend_view.cell(component, "Arıza süresi").endswith(" s")
        assert win.bit_trend_view.cell(component, "Değişim").isdigit()
