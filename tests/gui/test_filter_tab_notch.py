"""Filter sekmesi notch frekans ve Q kontrolleri — `F4-038`.

Kabul: uygulanan ayarlar kaydedilip yeniden yüklenir.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.filters import notch
from sonar_analyzer.processing.steps import StepKind
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.analysis_tools import CUTOFF_LABEL_CENTER, FilterTabError
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.model import FilterToolState, WorkspaceModel

pytestmark = pytest.mark.gui


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=8.0, sample_rate_hz=200.0))
    window.open_channel("ch0")
    return window


def _card(win: MainWindow):
    return win.right_dock.analysis_tools


def _select_notch(win: MainWindow, center: int, q: float, order: int = 4) -> None:
    card = _card(win)
    card.filter_response.setCurrentText("Notch")
    card.cutoff_frequency.setValue(center)
    card.quality_factor.setValue(q)
    card.order.setValue(order)


# --------------------------------------------------------------------------- #
# alanlar
# --------------------------------------------------------------------------- #


def test_notch_is_offered_in_the_response_selector(win: MainWindow) -> None:
    card = _card(win)
    values = [card.filter_response.itemText(i) for i in range(card.filter_response.count())]
    assert "Notch" in values


def test_the_q_field_appears_only_for_notch(win: MainWindow) -> None:
    card = _card(win)

    card.filter_response.setCurrentText("Low-pass")
    assert card.quality_factor.isHidden()

    card.filter_response.setCurrentText("Notch")
    assert not card.quality_factor.isHidden()
    assert card.high_cutoff_frequency.isHidden()  # band alanı gizli kalır

    card.filter_response.setCurrentText("Band-pass")
    assert card.quality_factor.isHidden()


def test_the_first_field_is_labelled_center_frequency(win: MainWindow) -> None:
    card = _card(win)
    card.filter_response.setCurrentText("Notch")
    assert card.cutoff_label_text() == CUTOFF_LABEL_CENTER


def test_center_and_q_reach_the_step(win: MainWindow) -> None:
    _select_notch(win, center=50, q=25.0, order=3)

    step = _card(win).build_filter_chain("ch0", 200.0).steps[0]
    assert step.kind is StepKind.NOTCH
    assert step.parameters == {
        "sample_rate_hz": 200.0,
        "center_hz": 50.0,
        "q": 25.0,
        "order": 3,
    }


def test_a_center_beyond_nyquist_is_rejected(win: MainWindow) -> None:
    _select_notch(win, center=150, q=30.0)  # Nyquist 100
    with pytest.raises(FilterTabError, match="Nyquist"):
        _card(win).build_filter_chain("ch0", 200.0)


def test_apply_notch_from_the_filter_tab_draws_the_result(win: MainWindow, qtbot: QtBot) -> None:
    card = _card(win)
    card.tabs.setCurrentIndex(0)
    _select_notch(win, center=50, q=30.0, order=4)
    card.show_filtered_data.setChecked(True)

    x, _raw = win.plot_panel.curve_data()
    card.apply_filter_button.click()
    qtbot.waitUntil(lambda: win.plot_panel.has_processed_overlay, timeout=10_000)

    processed = win.plot_panel.processed_overlay_values()
    source = MockRecordingRepository(duration_s=8.0, sample_rate_hz=200.0)
    full = source.query("ch0", source.metadata().time_range).values
    indices = np.rint(x * 200).astype(np.int64)
    assert np.allclose(processed, notch(full, 200.0, 50.0, 30.0, 4)[indices], atol=1e-9)


# --------------------------------------------------------------------------- #
# kaydet / yeniden yükle
# --------------------------------------------------------------------------- #


def test_settings_are_captured_into_the_workspace(win: MainWindow) -> None:
    _select_notch(win, center=60, q=12.5, order=6)
    _card(win).show_filtered_data.setChecked(True)

    state = win.capture_workspace().filter_tool
    assert state.response == "Notch"
    assert state.cutoff_hz == 60
    assert abs(state.q - 12.5) < 1e-9
    assert state.order == 6
    assert state.show_filtered is True


def test_settings_are_restored_from_a_workspace(win: MainWindow) -> None:
    model = WorkspaceModel(
        filter_tool=FilterToolState(
            family="Butterworth",
            response="Notch",
            cutoff_hz=45,
            high_cutoff_hz=310,
            q=7.5,
            order=5,
            show_filtered=True,
        )
    )
    win.apply_workspace(model)

    card = _card(win)
    assert card.filter_response.currentText() == "Notch"
    assert card.cutoff_frequency.value() == 45
    assert abs(card.quality_factor.value() - 7.5) < 1e-9
    assert card.order.value() == 5
    assert card.show_filtered_data.isChecked()
    # Yanıt türüne göre alan görünürlüğü de yeniden kurulur.
    assert not card.quality_factor.isHidden()
    assert card.cutoff_label_text() == CUTOFF_LABEL_CENTER


def test_settings_survive_a_save_and_reload_round_trip(win: MainWindow, tmp_path: Path) -> None:
    _select_notch(win, center=70, q=18.0, order=7)
    _card(win).show_filtered_data.setChecked(True)

    destination = win.save_workspace(tmp_path / "ws.json")

    # Alanları başka değerlere kaydır, sonra dosyadan geri yükle.
    _card(win).filter_response.setCurrentText("Low-pass")
    _card(win).cutoff_frequency.setValue(10)
    _card(win).quality_factor.setValue(1.0)
    _card(win).order.setValue(1)
    _card(win).show_filtered_data.setChecked(False)

    win.restore_workspace(destination)

    card = _card(win)
    assert card.filter_response.currentText() == "Notch"
    assert card.cutoff_frequency.value() == 70
    assert abs(card.quality_factor.value() - 18.0) < 1e-9
    assert card.order.value() == 7
    assert card.show_filtered_data.isChecked()


def test_a_workspace_without_filter_settings_keeps_the_defaults(win: MainWindow) -> None:
    # Eski belgelerde "filter_tool" bölümü yok — varsayılanlara düşer.
    document = WorkspaceModel().to_dict()
    del document["filter_tool"]
    model = WorkspaceModel.from_dict(document)

    assert model.filter_tool == FilterToolState()
    win.apply_workspace(model)
    assert _card(win).filter_response.currentText() == "Low-pass"
