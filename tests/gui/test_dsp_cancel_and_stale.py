"""DSP iptal ve eski sonuç denetimi — `F4-004`.

Kabul: iptal edilen veya eski seçime ait sonuç grafiğe uygulanmaz.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from numpy.typing import NDArray
from pytestqt.qtbot import QtBot

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.ui.dsp_runner import DspRunner

pytestmark = pytest.mark.gui


def _values(n: int = 1_500_000) -> NDArray[np.float64]:
    return np.linspace(-2.0, 2.0, n, dtype=np.float64)


def _chain(factor: float) -> ProcessingChain:
    return ProcessingChain(
        [
            ProcessingStep(StepKind.ABS, "ch0", {}),
            ProcessingStep(StepKind.SCALE, "ch0", {"factor": factor}),
            ProcessingStep(StepKind.MOVING_AVERAGE, "ch0", {"window": 7}),
        ]
    )


class _Collector:
    def __init__(self, runner: DspRunner) -> None:
        self.ready: list[int] = []
        self.stale: list[int] = []
        self.cancelled: list[int] = []
        runner.result_ready.connect(self._on_ready)
        runner.stale.connect(self._on_stale)
        runner.cancelled.connect(self._on_cancelled)

    def _on_ready(self, job_id: int, _cid: str, _res: object) -> None:
        self.ready.append(job_id)

    def _on_stale(self, job_id: int, _cid: str) -> None:
        self.stale.append(job_id)

    def _on_cancelled(self, job_id: int, _cid: str) -> None:
        self.cancelled.append(job_id)


def test_cancelled_job_result_is_not_applied(qtbot: QtBot) -> None:
    runner = DspRunner()
    seen = _Collector(runner)

    job_id = runner.submit(_chain(2.0), _values(), "ch0")
    runner.cancel(job_id)

    runner.wait_all(20_000)
    qtbot.waitUntil(lambda: seen.cancelled == [job_id], timeout=5_000)
    assert seen.ready == []  # grafiğe uygulanmadı


def test_cancel_all_suppresses_every_in_flight_result(qtbot: QtBot) -> None:
    runner = DspRunner()
    seen = _Collector(runner)

    ids = [runner.submit(_chain(float(k)), _values(), "ch0") for k in (1, 2, 3)]
    runner.cancel_all()

    runner.wait_all(20_000)
    qtbot.waitUntil(lambda: sorted(seen.cancelled) == sorted(ids), timeout=5_000)
    assert seen.ready == []


def test_result_for_a_stale_selection_is_not_applied(qtbot: QtBot) -> None:
    runner = DspRunner()
    seen = _Collector(runner)

    runner.set_selection("ch0@[0,10]")
    job_id = runner.submit(_chain(2.0), _values(), "ch0")

    # Kullanıcı seçimi değiştirdi; iş hâlâ eski seçime bağlı.
    runner.set_selection("ch0@[10,20]")

    runner.wait_all(20_000)
    qtbot.waitUntil(lambda: seen.stale == [job_id], timeout=5_000)
    assert seen.ready == []  # eski seçime ait sonuç uygulanmadı
    assert not runner.is_current(job_id)


def test_result_for_the_current_selection_is_applied(qtbot: QtBot) -> None:
    runner = DspRunner()
    seen = _Collector(runner)

    runner.set_selection("ch0@[0,10]")
    job_id = runner.submit(_chain(2.0), _values(200_000), "ch0")

    with qtbot.waitSignal(runner.result_ready, timeout=15_000):
        pass
    runner.wait_all()

    assert seen.ready == [job_id]
    assert seen.stale == [] and seen.cancelled == []


def test_returning_to_the_original_selection_revives_currency(qtbot: QtBot) -> None:
    runner = DspRunner()
    runner.set_selection("A")
    job_id = runner.submit(_chain(1.0), _values(50_000), "ch0")
    runner.set_selection("B")
    assert not runner.is_current(job_id)
    runner.set_selection("A")  # geri dönüldü
    assert runner.is_current(job_id)
    qtbot.waitUntil(lambda: not runner.busy, timeout=10_000)
    runner.wait_all()
