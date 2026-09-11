"""Kaydet/aç sonrası analiz tekrarı — `F4-088`.

Kabul: aynı kaynak ve parametreler aynı sayısal çıktıları üretir.

`F4-077` oturumun **yeniden kurulduğunu** gösterdi (zincir aynı, türetilmiş
kanal aynı veriyi döndürüyor). Burada sorulan daha ileri bir soru: o
oturumdan çıkan **analiz sonuçları** — FFT, PSD, STFT ve istatistik —
sayısal olarak aynı mı? Yeniden açılan bir oturumun aynı grafiği çizmesi
yetmez; aynı sayıları üretmesi gerekir.

Ölçüt yaklaşıklık değil, `np.array_equal` ile **bit düzeyinde** eşitliktir:
aynı girdi + aynı parametreler ikili düzeyde belirlenimci bir NumPy
hesabıdır; eşit olmamaları bir yerde saklanmamış bir parametre olduğunu
gösterirdi.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.analysis.psd import welch_psd
from sonar_analyzer.analysis.spectrum import one_sided_fft
from sonar_analyzer.analysis.statistics import summarize
from sonar_analyzer.analysis.stft import stft
from sonar_analyzer.analysis.windows import WindowKind
from sonar_analyzer.domain.derived_channel_definition import DerivedChannelDefinition
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.repository.derived_repository import DerivedChannelRepository
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

DURATION_S = 8.0
RATE_HZ = 200.0
SEGMENT = 128


def _window(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_repository(
        MockRecordingRepository(duration_s=DURATION_S, sample_rate_hz=RATE_HZ, seed=11)
    )
    window.open_channel("ch0")
    return window


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    return _window(qtbot)


def _furnish(win: MainWindow) -> None:
    """Oturuma bir işlem zinciri ve iki türetilmiş kanal koyar."""
    win.right_dock.analysis_tools.step_editor.set_chain(
        ProcessingChain(
            [
                ProcessingStep.default(StepKind.SCALE, "ch0").with_parameters(factor=1.75),
                ProcessingStep.default(StepKind.MOVING_AVERAGE, "ch0").with_parameters(window=5),
            ]
        )
    )
    repository = win.repository
    assert isinstance(repository, DerivedChannelRepository)
    repository.add(
        DerivedChannelDefinition(name="Fark", inputs=("ch0", "ch1"), expression="ch0 - ch1")
    )
    repository.add(
        DerivedChannelDefinition(
            name="Yumuşak",
            inputs=("ch0",),
            chain=ProcessingChain(
                [ProcessingStep.default(StepKind.MOVING_AVERAGE, "ch0").with_parameters(window=9)]
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


def _values(win: MainWindow, name: str) -> NDArray[Any]:
    """Adı verilen kanalın tam çözünürlüklü verisi."""
    repository = win.repository
    assert repository is not None
    channel = next(item for item in repository.channels() if item.name == name or item.id == name)
    return repository.query(channel.id, repository.metadata().time_range).values


def _analysed(win: MainWindow, name: str) -> NDArray[np.float64]:
    """Kanal verisi + oturumun işlem zinciri — analiz girdisi."""
    chain = win.right_dock.analysis_tools.step_editor.chain()
    return chain.run(_values(win, name)).values


# --------------------------------------------------------------------------- #
# analiz girdisi ayni
# --------------------------------------------------------------------------- #


def test_the_raw_channel_data_is_identical(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)
    assert np.array_equal(_values(other, "ch0"), _values(win, "ch0"))


def test_the_processed_input_is_identical(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    """Zincir geri yüklendiğinde analiz girdisi bit düzeyinde aynı."""
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)
    assert np.array_equal(_analysed(other, "ch0"), _analysed(win, "ch0"))


# --------------------------------------------------------------------------- #
# FFT
# --------------------------------------------------------------------------- #


def test_the_fft_is_identical_after_a_reload(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)

    before = one_sided_fft(_analysed(win, "ch0"), RATE_HZ, window=WindowKind.HANN)
    after = one_sided_fft(_analysed(other, "ch0"), RATE_HZ, window=WindowKind.HANN)

    assert np.array_equal(after.amplitudes, before.amplitudes)
    assert np.array_equal(after.frequencies_hz, before.frequencies_hz)
    assert after.peak_frequency_hz == before.peak_frequency_hz
    assert after.peak_amplitude == before.peak_amplitude


@pytest.mark.parametrize(
    "window_kind", [WindowKind.RECTANGULAR, WindowKind.HANN, WindowKind.HAMMING]
)
def test_the_fft_matches_for_every_window(
    win: MainWindow, qtbot: QtBot, tmp_path: Path, window_kind: WindowKind
) -> None:
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)
    before = one_sided_fft(_analysed(win, "ch0"), RATE_HZ, window=window_kind)
    after = one_sided_fft(_analysed(other, "ch0"), RATE_HZ, window=window_kind)
    assert np.array_equal(after.amplitudes, before.amplitudes)


# --------------------------------------------------------------------------- #
# PSD
# --------------------------------------------------------------------------- #


def test_the_psd_is_identical_after_a_reload(win: MainWindow, qtbot: QtBot, tmp_path: Path) -> None:
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)

    before = welch_psd(
        _analysed(win, "ch0"), RATE_HZ, window=WindowKind.HANN, segment_length=SEGMENT
    )
    after = welch_psd(
        _analysed(other, "ch0"), RATE_HZ, window=WindowKind.HANN, segment_length=SEGMENT
    )

    assert np.array_equal(after.density, before.density)
    assert after.integrated_power == before.integrated_power
    assert after.segment_count == before.segment_count


# --------------------------------------------------------------------------- #
# STFT
# --------------------------------------------------------------------------- #


def test_the_stft_matrix_is_identical_after_a_reload(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)

    before = stft(
        _analysed(win, "ch0"),
        RATE_HZ,
        segment_length=SEGMENT,
        overlap=0.5,
        window=WindowKind.HANN,
    )
    after = stft(
        _analysed(other, "ch0"),
        RATE_HZ,
        segment_length=SEGMENT,
        overlap=0.5,
        window=WindowKind.HANN,
    )

    assert after.magnitudes.shape == before.magnitudes.shape
    assert np.array_equal(after.magnitudes, before.magnitudes)
    assert np.array_equal(after.times_s, before.times_s)
    assert np.array_equal(after.peak_frequencies_hz(), before.peak_frequencies_hz())


# --------------------------------------------------------------------------- #
# istatistik
# --------------------------------------------------------------------------- #


def test_the_statistics_are_identical_after_a_reload(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)

    before = summarize(_analysed(win, "ch0"))
    after = summarize(_analysed(other, "ch0"))

    assert after == before


# --------------------------------------------------------------------------- #
# turetilmis kanallarda da ayni
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["Fark", "Yumuşak"])
def test_a_derived_channel_analyses_the_same_after_a_reload(
    win: MainWindow, qtbot: QtBot, tmp_path: Path, name: str
) -> None:
    _furnish(win)
    other = _reopened(win, qtbot, tmp_path)

    before = one_sided_fft(_values(win, name), RATE_HZ, window=WindowKind.HANN)
    after = one_sided_fft(_values(other, name), RATE_HZ, window=WindowKind.HANN)

    assert np.array_equal(after.amplitudes, before.amplitudes)
    assert summarize(_values(other, name)) == summarize(_values(win, name))


# --------------------------------------------------------------------------- #
# parametreler degisirse sonuc da degismeli
# --------------------------------------------------------------------------- #


def test_a_different_window_gives_a_different_spectrum(win: MainWindow) -> None:
    """Karşılaştırma noktası: testler gerçekten bir şey ölçüyor."""
    data = _analysed(win, "ch0")
    rectangular = one_sided_fft(data, RATE_HZ, window=WindowKind.RECTANGULAR)
    hann = one_sided_fft(data, RATE_HZ, window=WindowKind.HANN)
    assert not np.array_equal(rectangular.amplitudes, hann.amplitudes)


def test_a_different_chain_gives_a_different_analysis(win: MainWindow) -> None:
    _furnish(win)
    before = _analysed(win, "ch0")
    win.right_dock.analysis_tools.step_editor.set_chain(
        ProcessingChain([ProcessingStep.default(StepKind.ABS, "ch0")])
    )
    assert not np.array_equal(_analysed(win, "ch0"), before)


def test_the_repeatability_survives_two_round_trips(
    win: MainWindow, qtbot: QtBot, tmp_path: Path
) -> None:
    """Tur idempotenttir: kaydet/aç/kaydet/aç aynı sayıları verir."""
    _furnish(win)
    first = _reopened(win, qtbot, tmp_path)
    second_path = tmp_path / "ikinci.sonarws"
    first.save_workspace(second_path)
    second = _window(qtbot)
    second.restore_workspace(second_path)

    before = one_sided_fft(_analysed(win, "ch0"), RATE_HZ, window=WindowKind.HANN)
    after = one_sided_fft(_analysed(second, "ch0"), RATE_HZ, window=WindowKind.HANN)
    assert np.array_equal(after.amplitudes, before.amplitudes)
