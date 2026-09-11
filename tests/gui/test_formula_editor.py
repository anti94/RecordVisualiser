"""Custom sekmesindeki formül editörü — `F4-073`.

Kabul: geçerli ifade Derived kanalı üretir; hata ilgili alanda görünür.

"Derived kanalı üretir" uçtan uca denetlenir: kullanıcı ifadeyi ve adı
yazar, düğmeye basar, kanal `Derived/` ağacında belirir ve sorgulandığında
formülün gerçekten hesapladığı veriyi döndürür. "İlgili alanda" ise hata
metninin **hangi** etikette çıktığıyla denetlenir — ifade hatası ifade
alanında, ad hatası ad alanında, biri varken diğeri boş.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.derived_channel_definition import DerivedChannelDefinition
from sonar_analyzer.repository.derived_repository import DerivedChannelRepository
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.cards.formula_editor import (
    EMPTY_HINT,
    NAME_REQUIRED_MESSAGE,
    NO_CHANNEL_MESSAGE,
    FormulaEditor,
)
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def editor(qtbot: QtBot) -> FormulaEditor:
    widget = FormulaEditor()
    qtbot.addWidget(widget)
    widget.set_channels(list(MockRecordingRepository(duration_s=2.0).channels()))
    return widget


# --------------------------------------------------------------------------- #
# kullanilabilir kanallar
# --------------------------------------------------------------------------- #


def test_a_fresh_editor_says_no_channels_are_available(qtbot: QtBot) -> None:
    widget = FormulaEditor()
    qtbot.addWidget(widget)
    assert widget.available_names() == []
    assert widget.channels_hint.text() == EMPTY_HINT
    assert not widget.add_button.isEnabled()


def test_the_hint_lists_the_channels_that_can_be_written(editor: FormulaEditor) -> None:
    names = editor.available_names()
    assert "ch0" in names and "ch1" in names
    for name in names:
        assert name in editor.channels_hint.text()


def test_ids_that_are_not_identifiers_are_not_offered(qtbot: QtBot) -> None:
    """`derived:ab12` formülde yazılamaz; ipucunda da görünmez."""
    widget = FormulaEditor()
    qtbot.addWidget(widget)
    base = list(MockRecordingRepository(duration_s=2.0).channels())
    repository = DerivedChannelRepository(MockRecordingRepository(duration_s=2.0))
    derived = repository.add(DerivedChannelDefinition(name="Ölçek", inputs=("ch0",)))
    widget.set_channels([*base, derived])
    assert derived.id not in widget.available_names()
    assert derived.id not in widget.channels_hint.text()


# --------------------------------------------------------------------------- #
# hata ILGILI alanda gorunur
# --------------------------------------------------------------------------- #


def test_an_empty_editor_shows_no_error_at_all(editor: FormulaEditor) -> None:
    """Kullanıcı daha yazmaya başlamadan kırmızı uyarı çıkmaz."""
    assert editor.expression_error_text() == ""
    assert editor.name_error_text() == ""
    assert not editor.is_valid


def test_a_syntax_error_appears_under_the_expression_field(editor: FormulaEditor) -> None:
    editor.set_expression("ch0 +")
    assert "ayrıştırılamadı" in editor.expression_error_text()
    assert not editor.expression_error.isHidden()
    assert editor.name_error_text() == ""  # ad alani temiz
    assert not editor.add_button.isEnabled()


def test_an_unknown_channel_error_appears_under_the_expression_field(
    editor: FormulaEditor,
) -> None:
    editor.set_expression("ch0 + yok")
    assert "İzinli olmayan ad" in editor.expression_error_text()
    assert "yok" in editor.expression_error_text()
    assert editor.name_error_text() == ""


def test_a_forbidden_call_error_appears_under_the_expression_field(
    editor: FormulaEditor,
) -> None:
    editor.set_expression("open('x')")
    assert "İzinli olmayan" in editor.expression_error_text()
    assert not editor.is_valid


def test_a_constant_only_expression_is_an_expression_error_not_a_name_error(
    editor: FormulaEditor,
) -> None:
    """Kanalsız ifade adın değil ifadenin sorunudur."""
    editor.set_expression("2 * 3")
    editor.set_name("Sabit")
    assert editor.expression_error_text() == NO_CHANNEL_MESSAGE
    assert editor.name_error_text() == ""
    assert not editor.is_valid


def test_a_missing_name_appears_under_the_name_field(editor: FormulaEditor) -> None:
    editor.set_expression("ch0 * 2")
    assert editor.expression_error_text() == ""  # ifade alani temiz
    assert editor.name_error_text() == NAME_REQUIRED_MESSAGE
    assert not editor.name_error.isHidden()
    assert not editor.add_button.isEnabled()


def test_a_whitespace_only_name_still_counts_as_missing(editor: FormulaEditor) -> None:
    editor.set_expression("ch0 * 2")
    editor.set_name("   ")
    assert editor.name_error_text() == NAME_REQUIRED_MESSAGE


def test_the_name_error_is_not_shown_while_the_expression_is_broken(
    editor: FormulaEditor,
) -> None:
    """Bir seferde bir sorun: önce ifade düzelsin."""
    editor.set_expression("ch0 +")
    assert editor.expression_error_text() != ""
    assert editor.name_error_text() == ""


def test_fixing_the_expression_clears_its_error(editor: FormulaEditor) -> None:
    editor.set_expression("ch0 +")
    assert editor.expression_error_text() != ""
    editor.set_expression("ch0 + ch1")
    assert editor.expression_error_text() == ""
    assert editor.expression_error.isHidden()


# --------------------------------------------------------------------------- #
# gecerli ifade -> tanim
# --------------------------------------------------------------------------- #


def test_a_valid_expression_and_name_enable_the_button(editor: FormulaEditor) -> None:
    editor.set_expression("ch0 * 2 - ch1")
    editor.set_name("Fark")
    assert editor.is_valid
    assert editor.add_button.isEnabled()
    assert editor.expression_error_text() == ""
    assert editor.name_error_text() == ""


def test_the_definition_carries_the_expression_and_its_inputs(editor: FormulaEditor) -> None:
    editor.set_expression("ch0 * 2 - ch1")
    editor.set_name("Fark")
    definition = editor.definition()
    assert definition is not None
    assert definition.name == "Fark"
    assert definition.expression == "ch0 * 2 - ch1"
    assert definition.inputs == ("ch0", "ch1")


def test_no_definition_is_produced_while_invalid(editor: FormulaEditor) -> None:
    editor.set_expression("ch0 +")
    editor.set_name("Fark")
    assert editor.definition() is None


def test_validity_changes_are_announced(editor: FormulaEditor) -> None:
    seen: list[bool] = []
    editor.validity_changed.connect(seen.append)

    editor.set_expression("ch0 * 2")
    assert seen == []  # ad henuz yok
    editor.set_name("Iki kat")
    assert seen == [True]

    editor.set_expression("ch0 +")
    assert seen == [True, False]


def test_pressing_add_emits_the_definition(editor: FormulaEditor) -> None:
    emitted: list[object] = []
    editor.definition_requested.connect(emitted.append)

    editor.set_expression("ch0 + ch1")
    editor.set_name("Toplam")
    editor.add_button.click()

    assert len(emitted) == 1
    definition = emitted[0]
    assert isinstance(definition, DerivedChannelDefinition)
    assert definition.expression == "ch0 + ch1"
    assert definition.inputs == ("ch0", "ch1")


def test_an_invalid_editor_cannot_emit_anything(editor: FormulaEditor) -> None:
    """Düğme pasif olduğu için geçersiz tanım hiç gönderilemez."""
    editor.set_expression("ch0 +")
    editor.set_name("Kötü")
    received: list[object] = []
    editor.definition_requested.connect(received.append)
    editor.add_button.click()  # pasif düğme
    assert received == []


# --------------------------------------------------------------------------- #
# uctan uca: Derived kanali gercekten uretilir
# --------------------------------------------------------------------------- #


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=4.0, sample_rate_hz=50.0))
    return window


def _repo(win: MainWindow) -> DerivedChannelRepository:
    """Pencerenin kaynağı; `set_repository` onu `F4-069` ile sarar."""
    repository = win.repository
    assert isinstance(repository, DerivedChannelRepository)
    return repository


def test_the_window_wraps_the_repository_so_derived_channels_are_possible(
    win: MainWindow,
) -> None:
    assert isinstance(win.repository, DerivedChannelRepository)
    assert win.base_repository() is not win.repository
    assert win.base_repository() is _repo(win).base


def test_the_editor_learns_the_channels_of_the_open_recording(win: MainWindow) -> None:
    editor = win.right_dock.analysis_tools.formula_editor
    assert "ch0" in editor.available_names()


def test_a_valid_formula_creates_a_queryable_derived_channel(win: MainWindow) -> None:
    """Kabul kriterinin kendisi, uçtan uca."""
    editor = win.right_dock.analysis_tools.formula_editor
    before = len(_repo(win).channels())

    editor.set_expression("ch0 - ch1")
    editor.set_name("Fark")
    editor.add_button.click()

    channels = _repo(win).channels()
    assert len(channels) == before + 1
    derived = channels[-1]
    assert derived.path == "Derived/Fark"

    span = _repo(win).metadata().time_range
    result = _repo(win).query(derived.id, span)
    expected = _repo(win).query("ch0", span).values - _repo(win).query("ch1", span).values
    assert np.allclose(result.values, expected)
    assert len(result) == len(expected)


def test_the_new_channel_appears_in_the_channel_tree(win: MainWindow) -> None:
    editor = win.right_dock.analysis_tools.formula_editor
    editor.set_expression("ch0 * 2")
    editor.set_name("Iki kat")
    editor.add_button.click()
    assert any(channel.name == "Iki kat" for channel in _repo(win).channels())


def test_adding_a_derived_channel_is_logged(win: MainWindow) -> None:
    editor = win.right_dock.analysis_tools.formula_editor
    editor.set_expression("ch0 * 2")
    editor.set_name("Iki kat")
    editor.add_button.click()
    assert any("Derived/Iki kat" in line for line in win.bottom_dock.log_lines())


def test_the_raw_channels_are_untouched_by_the_new_derived_channel(
    win: MainWindow,
) -> None:
    span = _repo(win).metadata().time_range
    before = _repo(win).query("ch0", span).values.copy()

    editor = win.right_dock.analysis_tools.formula_editor
    editor.set_expression("ch0 * 100")
    editor.set_name("Yüz kat")
    editor.add_button.click()

    assert np.array_equal(_repo(win).query("ch0", span).values, before)


def test_the_derived_channel_can_be_plotted(win: MainWindow) -> None:
    editor = win.right_dock.analysis_tools.formula_editor
    editor.set_expression("ch0 + ch1")
    editor.set_name("Toplam")
    editor.add_button.click()

    derived = _repo(win).channels()[-1]
    win.open_channel(derived.id)
    assert win.plot_panel.channel is not None
    assert win.plot_panel.channel.id == derived.id
