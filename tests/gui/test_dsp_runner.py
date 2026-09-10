"""DSP işlerini worker üzerinden çalıştır — `F4-003`.

Kabul: uzun hesaplama UI'ı durdurmaz; güncel iş sonucu yayınlanır.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from numpy.typing import NDArray
from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.chain import ChainResult, ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.ui.dsp_runner import DspRunner

pytestmark = pytest.mark.gui


def _big(n: int = 2_000_000) -> NDArray[np.float64]:
    return np.linspace(-1.0, 1.0, n, dtype=np.float64)


def _chain(factor: float) -> ProcessingChain:
    return ProcessingChain(
        [
            ProcessingStep(StepKind.ABS, "ch0", {}),
            ProcessingStep(StepKind.SCALE, "ch0", {"factor": factor}),
            ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": 9}),
        ]
    )


def test_submit_returns_immediately_and_result_arrives_later(qtbot: QtBot) -> None:
    runner = DspRunner()
    captured: list[tuple[int, str, ChainResult]] = []

    def _on_ready(job_id: int, channel_id: str, result: object) -> None:
        assert isinstance(result, ChainResult)
        captured.append((job_id, channel_id, result))

    runner.result_ready.connect(_on_ready)

    started = time.perf_counter()
    job_id = runner.submit(_chain(2.0), _big(), "ch0")
    assert time.perf_counter() - started < 0.1  # submit bloklamadı
    assert job_id == 1

    with qtbot.waitSignal(runner.result_ready, timeout=15_000):
        pass
    assert runner.wait_all()

    jid, cid, result = captured[0]
    assert jid == 1 and cid == "ch0"
    assert result.values.shape == _big().shape
    assert result.step_count == 3


def test_only_the_latest_job_publishes_a_result(qtbot: QtBot) -> None:
    runner = DspRunner()
    fresh: list[int] = []
    stale: list[int] = []

    def _on_ready(job_id: int, _channel_id: str, _result: object) -> None:
        fresh.append(job_id)

    def _on_stale(job_id: int, _channel_id: str) -> None:
        stale.append(job_id)

    runner.result_ready.connect(_on_ready)
    runner.stale.connect(_on_stale)

    values = _big()
    ids = (
        runner.submit(_chain(2.0), values, "ch0"),
        runner.submit(_chain(3.0), values, "ch0"),
        runner.submit(_chain(5.0), values, "ch0"),
    )
    assert ids == (1, 2, 3)
    assert runner.latest_job_id == 3

    qtbot.waitUntil(lambda: not runner.busy, timeout=20_000)
    runner.wait_all()

    assert fresh == [3]  # yalnız en güncel iş yayınladı
    assert set(stale) <= {1, 2}  # eskiler atıldı


def test_is_current_tracks_the_latest_submission(qtbot: QtBot) -> None:
    runner = DspRunner()
    a = runner.submit(_chain(1.0), _big(50_000), "ch0")
    assert runner.is_current(a)
    b = runner.submit(_chain(2.0), _big(50_000), "ch0")
    assert not runner.is_current(a)
    assert runner.is_current(b)
    qtbot.waitUntil(lambda: not runner.busy, timeout=10_000)
    runner.wait_all()


def test_chain_error_is_reported_for_the_latest_job(qtbot: QtBot) -> None:
    runner = DspRunner()
    messages: list[str] = []

    def _on_failed(_job_id: int, message: str) -> None:
        messages.append(message)

    runner.failed.connect(_on_failed)

    bad = ProcessingChain([ProcessingStep(StepKind.ABS, "ch0", {})])
    with qtbot.waitSignal(runner.failed, timeout=10_000):
        runner.submit(bad, np.zeros((2, 2), dtype=np.float64), "ch0")
    runner.wait_all()
    assert messages and "tek boyutlu" in messages[0]


def test_ui_stays_responsive_during_a_long_job(qtbot: QtBot) -> None:
    runner = DspRunner()
    runner.submit(_chain(2.0), _big(3_000_000), "ch0")

    ticks = 0
    deadline = time.perf_counter() + 0.3
    while time.perf_counter() < deadline and runner.busy:
        qtbot.wait(10)  # olay döngüsü canlı
        ticks += 1
    assert ticks > 0  # iş sürerken UI olayları işlendi

    qtbot.waitUntil(lambda: not runner.busy, timeout=20_000)
    runner.wait_all()
