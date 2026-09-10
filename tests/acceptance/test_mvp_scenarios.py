"""MVP kullanıcı kabul senaryoları — `F3-078`.

Plan Bölüm 17.5'in beş kabul sorusunu operatör ve mühendis akışları
olarak koşar; her senaryo Bölüm 23 "Definition of Done" maddelerine
`SCENARIOS` tablosunda bağlanır (kanıt = bu testler).

`docs/acceptance/mvp-scenarios.md` insan-okur eşlemedir.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import Severity
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


#: (senaryo id, §17.5 sorusu, bağlı §23 DoD maddeleri, kanıt testi)
SCENARIOS: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "operator-bit-to-signal",
        "Operatör bir BIT FAIL'den ilgili sinyal anına en fazla iki etkileşimle gidebiliyor mu?",
        ("BIT/event satırından grafikte aynı zamana gidiliyor.",),
        "test_operator_reaches_signal_moment_in_two_interactions",
    ),
    (
        "engineer-compare-two-channels",
        "Test mühendisi iki kanalı aynı eksende karşılaştırabiliyor mu?",
        (
            "Kullanıcı kanalları grafiğe ekleyip kaldırabiliyor.",
            "Birden fazla grafik ortak X zaman ekseninde senkronize olabiliyor.",
        ),
        "test_engineer_compares_two_channels_on_one_axis",
    ),
    (
        "roi-statistics-readable",
        "Seçili zaman aralığının istatistiği (v1.0.0) anlaşılır mı?",
        ("Cursor ve region ölçümleri doğru.",),
        "test_selected_range_statistics_are_labelled_and_scoped",
    ),
    (
        "zoom-modes-unambiguous",
        "Kullanıcı X/Y zoom modunu yanlış yorumlamadan kullanabiliyor mu?",
        ("X, Y ve XY zoom davranışları tutarlı.",),
        "test_zoom_modes_are_unambiguous",
    ),
    (
        "workspace-round-trip",
        "Kaydedilen workspace yeniden açıldığında aynı düzen ve işlemler geliyor mu?",
        ("Workspace kaydet/aç işlevi temel düzeni koruyor.",),
        "test_workspace_reopens_with_same_layout_and_operations",
    ),
)

#: Bölüm 17.5'te listelenen kabul soruları (FFT v2 hariç — MVP kapsamı dışı).
SECTION_17_5_QUESTIONS = frozenset(question for _id, question, _dod, _evidence in SCENARIOS)


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.set_repository(MockRecordingRepository(duration_s=12.0))
    return window


# -- kanıt haritası -------------------------------------------


def test_every_17_5_scenario_has_a_linked_evidence_test() -> None:
    """Her senaryonun §23 DoD bağlantısı ve bu dosyada bir kanıt testi var."""
    module_tests = {name for name in globals() if name.startswith("test_")}
    for scenario_id, question, dod_items, evidence in SCENARIOS:
        assert question, scenario_id
        assert dod_items, f"{scenario_id}: §23 DoD bağlantısı eksik"
        assert evidence in module_tests, f"{scenario_id}: kanıt testi {evidence!r} yok"
    assert len(SECTION_17_5_QUESTIONS) == 5


# -- operatör -----------------------------------------------


def test_operator_reaches_signal_moment_in_two_interactions(win: MainWindow) -> None:
    """§17.5: BIT FAIL -> ilgili sinyal anı, en fazla iki etkileşim."""
    win.open_channel("ch0")
    panel = win.plot_panel
    probe = MockRecordingRepository(duration_s=12.0)
    span = probe.metadata().time_range
    events = probe.events(span)
    win.bottom_dock.set_events(events, start_ns=span.start_ns)

    fail_event = next(e for e in events if e.severity is Severity.ERROR)

    interactions = 0
    # Etkileşim 1: olay satırını seç.
    win.bottom_dock.event_selected.emit(fail_event)
    interactions += 1
    # Etkileşim 2: satırı etkinleştir (çift tık / Enter).
    win.bottom_dock.event_activated.emit(fail_event)
    interactions += 1

    assert interactions <= 2
    x_min, x_max = win.plot_panel.visible_x_range()
    centre_ns = panel.timestamp_ns_for_x((x_min + x_max) / 2.0)
    assert abs(centre_ns - fail_event.timestamp_ns) < 2_000_000  # grafik hizalandı


# -- mühendis ---------------------------------------------


def test_engineer_compares_two_channels_on_one_axis(win: MainWindow) -> None:
    """§17.5: aynı birimli iki kanal aynı Y ekseninde karşılaştırılır."""
    win.open_channel("ch2")  # Accel X [g]
    win.left_dock.channels_add_requested.emit(["ch3"])  # Accel Y [g]

    assert win.plot_panel.plotted_channel_ids() == ["ch2", "ch3"]
    assert win.plot_panel.axis_for_channel("ch2") == win.plot_panel.axis_for_channel("ch3")
    assert not win.plot_panel.right_axis_visible  # tek birim -> tek eksen
    # Ortak X zaman ekseni: iki seri aynı ankoru paylaşır.
    assert win.plot_panel.time_anchor_ns is not None


# -- ROI istatistiği --------------------------------------


def test_selected_range_statistics_are_labelled_and_scoped(win: MainWindow, qtbot: QtBot) -> None:
    """§17.5: seçili zaman aralığının istatistiği anlaşılır (etiketli + pencereli)."""
    win.open_channel("ch0")
    plain_title = win.dashboard.statistics.title()

    win.plot_panel.set_time_region(2.0, 6.0)
    # F4-061: analiz yüzeyleri en fazla 20 Hz boyanır; seçim bir sonraki
    # karede yansır. Kabul ölçütü değişmez, yalnız kareyi bekleriz.
    qtbot.waitUntil(lambda: win.dashboard.statistics.title() != plain_title, timeout=1_000)

    scoped_title = win.dashboard.statistics.title()
    assert scoped_title != plain_title
    assert "2" in scoped_title and "6" in scoped_title  # pencere sınırları görünür
    for field in ("Mean", "Min", "Max"):
        assert win.dashboard.statistics.field_value(field) not in ("", "—")


# -- zoom modları ---------------------------------------


def test_zoom_modes_are_unambiguous(win: MainWindow) -> None:
    """§17.5: X yalnız X'i, Y yalnız Y'yi ölçekler; kip grafikte okunur."""
    win.open_channel("ch0")

    win.set_zoom_mode_x()
    assert win.plot_panel.zoom_mode == "x"
    x0, x1, y0, y1 = win.plot_panel.visible_range()
    win.plot_panel.zoom(0.5)
    nx0, nx1, ny0, ny1 = win.plot_panel.visible_range()
    assert (nx1 - nx0) < (x1 - x0) - 1e-6
    assert abs((ny1 - ny0) - (y1 - y0)) < 1e-6

    win.set_zoom_mode_y()
    assert win.plot_panel.zoom_mode == "y"
    x0, x1, y0, y1 = win.plot_panel.visible_range()
    win.plot_panel.zoom(0.5)
    nx0, nx1, ny0, ny1 = win.plot_panel.visible_range()
    assert abs((nx1 - nx0) - (x1 - x0)) < 1e-6
    assert (ny1 - ny0) < (y1 - y0) - 1e-6


# -- workspace round-trip -----------------------------


def test_workspace_reopens_with_same_layout_and_operations(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    """§17.5: kaydedilen workspace aynı düzen ve işlemlerle geri gelir."""
    win.open_channel("ch2")
    win.left_dock.channels_add_requested.emit(["ch3"])
    win.plot_panel.set_zoom_mode("x")
    win.plot_panel.set_x_range(2.0, 9.0)
    win.plot_tool_bar.markers_checkbox.setChecked(False)

    saved = win.save_workspace(tmp_path / "mvp-session.json")

    fresh = MainWindow()
    qtbot.addWidget(fresh)
    fresh.set_repository(MockRecordingRepository(duration_s=12.0))
    fresh.restore_workspace(saved)

    assert fresh.plot_panel.plotted_channel_ids() == ["ch2", "ch3"]
    assert fresh.plot_panel.zoom_mode == "x"
    fx0, fx1 = fresh.plot_panel.visible_x_range()
    assert abs(fx0 - 2.0) < 1e-6 and abs(fx1 - 9.0) < 1e-6
    assert fresh.plot_tool_bar.markers_checkbox.isChecked() is False
