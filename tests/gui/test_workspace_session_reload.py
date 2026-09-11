"""Analiz oturumunun ve türetilmiş kanalların yüklenmesi — `F4-077`.

Kabul: yeniden açılan oturum **aynı işlem sonuçlarını** üretir.

Ölçüt eşitlik değil, *sayısal* eşitliktir: aynı girdiye uygulanan zincir
ve aynı pencereden sorgulanan türetilmiş kanal, oturum kaydedilip yeni
bir pencerede açıldıktan sonra **bit düzeyinde aynı** diziyi vermelidir.
Bir adımın sırası, parametresi ya da açık/kapalı durumu kaybolsaydı bu
test düşerdi.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.derived_channel_definition import DerivedChannelDefinition
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.repository.derived_repository import DerivedChannelRepository
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.workspace.migrate import migrate_document
from sonar_analyzer.workspace.model import WORKSPACE_SCHEMA_VERSION, WorkspaceModel

pytestmark = pytest.mark.gui

DURATION_S = 8.0
RATE_HZ = 50.0
#: Zincirin uygulandığı sabit girdi — iki oturumda da aynı.
PROBE = np.linspace(-3.0, 5.0, 64)


def _window(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(MockRecordingRepository(duration_s=DURATION_S, sample_rate_hz=RATE_HZ))
    window.open_channel("ch0")
    return window


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    return _window(qtbot)


def _chain() -> ProcessingChain:
    """Sıra, parametre ve açık/kapalı durumu ayrı ayrı önemli olan bir zincir."""
    scale = ProcessingStep.default(StepKind.SCALE, "ch0").with_parameters(factor=2.5)
    offset = ProcessingStep.default(StepKind.OFFSET, "ch0").with_parameters(delta=-1.25)
    smooth = ProcessingStep.default(StepKind.MOVING_AVERAGE, "ch0").with_parameters(window=5)
    disabled = ProcessingStep(
        kind=StepKind.ABS, input_channel_id="ch0", parameters={}, enabled=False
    )
    return ProcessingChain([scale, offset, smooth, disabled])


def _furnish(win: MainWindow) -> None:
    """Oturuma hem bir işlem zinciri hem de bir türetilmiş kanal koyar."""
    win.right_dock.analysis_tools.step_editor.set_chain(_chain())
    repository = win.repository
    assert isinstance(repository, DerivedChannelRepository)
    repository.add(
        DerivedChannelDefinition(name="Fark", inputs=("ch0", "ch1"), expression="ch0 * 2 - ch1")
    )
    repository.add(
        DerivedChannelDefinition(
            name="Yumuşak",
            inputs=("ch0",),
            chain=ProcessingChain(
                [ProcessingStep.default(StepKind.MOVING_AVERAGE, "ch0").with_parameters(window=7)]
            ),
        )
    )
    win.set_recording(repository.metadata(), repository.channels())
    win.open_channel("ch0")


def _reopened(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> MainWindow:
    target = win.save_workspace(tmp_path / "oturum.sonarws")
    other = _window(qtbot)
    other.restore_workspace(target)
    return other


def _derived_values(win: MainWindow, name: str) -> NDArray[Any]:
    repository = win.repository
    assert isinstance(repository, DerivedChannelRepository)
    channel = next(item for item in repository.channels() if item.name == name)
    return repository.query(channel.id, repository.metadata().time_range).values


# --------------------------------------------------------------------------- #
# sema
# --------------------------------------------------------------------------- #


def test_the_processing_chain_arrived_in_schema_version_three() -> None:
    """Zincir v3 ile geldi; sonraki sürümler üstüne ekler."""
    assert WORKSPACE_SCHEMA_VERSION >= 3


def test_the_document_carries_the_processing_chain() -> None:
    assert "processing_chain" in WorkspaceModel().to_dict()
    assert WorkspaceModel().processing_chain == []


def test_a_version_two_document_migrates_without_losing_anything() -> None:
    legacy: dict[str, object] = {
        "schema_version": 2,
        "source_paths": ["kayit.bin"],
        "panels": [{"channel_ids": ["ch0"]}],
        "annotations": [],
        "derived_channels": [],
        "series_styles": {},
    }
    migrated = migrate_document(legacy)
    assert migrated["schema_version"] == WORKSPACE_SCHEMA_VERSION
    assert migrated["processing_chain"] == []
    assert migrated["source_paths"] == ["kayit.bin"]


def test_a_v0_document_still_reaches_the_current_version() -> None:
    legacy: dict[str, object] = {"schema_version": 0, "open_files": ["a.bin"], "panels": []}
    model = WorkspaceModel.from_dict(migrate_document(legacy))
    assert model.schema_version == WORKSPACE_SCHEMA_VERSION
    assert model.processing_chain == []


# --------------------------------------------------------------------------- #
# zincir kaydedilir ve ayni sonucu uretir
# --------------------------------------------------------------------------- #


def test_the_capture_holds_the_processing_chain(win: MainWindow) -> None:
    _furnish(win)
    model = win.capture_workspace()
    assert [str(record["kind"]) for record in model.processing_chain] == [
        "scale",
        "offset",
        "moving_average",
        "abs",
    ]


def test_the_saved_file_holds_the_chain_parameters(win: MainWindow, tmp_path: Path) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")
    document = json.loads(target.read_text(encoding="utf-8"))
    steps = document["processing_chain"]
    assert steps[0]["parameters"]["factor"] == 2.5
    assert steps[1]["parameters"]["delta"] == -1.25
    assert steps[2]["parameters"]["window"] == 5
    assert steps[3]["enabled"] is False


def test_the_reopened_chain_is_identical(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    _furnish(win)
    before = win.right_dock.analysis_tools.step_editor.chain()

    after = _reopened(win, qtbot, tmp_path).right_dock.analysis_tools.step_editor.chain()

    assert after.to_list() == before.to_list()
    assert after.signature() == before.signature()
    assert [step.enabled for step in after.steps] == [True, True, True, False]


def test_the_reopened_chain_produces_the_same_values(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    """Kabul kriterinin kendisi: aynı girdi, bit düzeyinde aynı çıktı."""
    _furnish(win)
    before = win.right_dock.analysis_tools.step_editor.chain().run(PROBE)

    after = _reopened(win, qtbot, tmp_path).right_dock.analysis_tools.step_editor.chain().run(PROBE)

    assert np.array_equal(after.values, before.values)
    assert after.applied == before.applied


def test_a_disabled_step_stays_disabled_after_reload(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    """Kapalı adım açılsaydı sonuç **gerçekten** değişirdi."""
    _furnish(win)
    reopened = _reopened(win, qtbot, tmp_path)
    chain = reopened.right_dock.analysis_tools.step_editor.chain()

    assert len(chain.enabled_steps) == 3
    assert [step.enabled for step in chain.steps][-1] is False

    # Aynı zincir, son adım açık: farklı bir sonuç verir.
    enabled = ProcessingChain([*chain.steps[:-1], ProcessingStep.default(StepKind.ABS, "ch0")])
    assert not np.array_equal(chain.run(PROBE).values, enabled.run(PROBE).values)


def test_an_empty_chain_reloads_as_empty(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    win.right_dock.analysis_tools.step_editor.set_chain(ProcessingChain())
    reopened = _reopened(win, qtbot, tmp_path)
    assert reopened.right_dock.analysis_tools.step_editor.chain().steps == []


def test_a_broken_step_is_explained_and_does_not_sink_the_session(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    target = win.save_workspace(tmp_path / "oturum.sonarws")
    document = json.loads(target.read_text(encoding="utf-8"))
    document["processing_chain"][0]["kind"] = "bilinmeyen_adim"
    target.write_text(json.dumps(document), encoding="utf-8")

    other = _window(qtbot)
    other.restore_workspace(target)

    assert any("İşlem zinciri geri yüklenemedi" in line for line in other.bottom_dock.log_lines())
    # Oturumun kalani yuklendi.
    repository = other.repository
    assert isinstance(repository, DerivedChannelRepository)
    assert len(repository.definitions()) == 2


# --------------------------------------------------------------------------- #
# turetilmis kanallar ayni sonucu uretir
# --------------------------------------------------------------------------- #


def test_a_formula_channel_reproduces_its_values(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    before = _derived_values(win, "Fark")
    after = _derived_values(_reopened(win, qtbot, tmp_path), "Fark")
    assert np.array_equal(after, before)


def test_a_chain_channel_reproduces_its_values(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    before = _derived_values(win, "Yumuşak")
    after = _derived_values(_reopened(win, qtbot, tmp_path), "Yumuşak")
    assert np.array_equal(after, before)


def test_the_derived_channel_ids_are_stable_across_sessions(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    """Kimlik tariften türer; yeniden açılan oturumda aynı kimlik gelir."""
    _furnish(win)
    repository = win.repository
    assert isinstance(repository, DerivedChannelRepository)
    before = sorted(definition.derived_id for definition in repository.definitions())

    reopened = _reopened(win, qtbot, tmp_path).repository
    assert isinstance(reopened, DerivedChannelRepository)
    after = sorted(definition.derived_id for definition in reopened.definitions())

    assert after == before


def test_the_derived_channels_keep_their_order_and_names(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    reopened = _reopened(win, qtbot, tmp_path).repository
    assert isinstance(reopened, DerivedChannelRepository)
    assert [definition.name for definition in reopened.definitions()] == ["Fark", "Yumuşak"]


def test_reopening_twice_is_still_identical(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    """Tur idempotenttir: kaydet/aç/kaydet/aç aynı sonucu verir."""
    _furnish(win)
    first = _reopened(win, qtbot, tmp_path)
    second_path = tmp_path / "ikinci.sonarws"
    first.save_workspace(second_path)
    second = _window(qtbot)
    second.restore_workspace(second_path)

    assert np.array_equal(_derived_values(second, "Fark"), _derived_values(win, "Fark"))
    assert (
        second.right_dock.analysis_tools.step_editor.chain().signature()
        == win.right_dock.analysis_tools.step_editor.chain().signature()
    )


def test_the_raw_channels_are_unchanged_by_a_reload(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    repository = win.repository
    assert repository is not None
    span = repository.metadata().time_range
    before = repository.query("ch0", span).values

    reopened = _reopened(win, qtbot, tmp_path).repository
    assert reopened is not None
    assert np.array_equal(reopened.query("ch0", span).values, before)
