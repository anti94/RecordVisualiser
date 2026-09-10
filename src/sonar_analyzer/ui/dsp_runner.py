"""DSP işlerini worker üzerinden çalıştır — `F4-003`.

Bir `ProcessingChain.run()` büyük bir kanalda milyonlarca örnek üzerinde
çalışabilir; GUI thread'inde yapılırsa pencere donar. `DspRunner` her
işi kısa ömürlü bir `QThread`'e taşır ve **yalnız en güncel** işin
sonucunu yayınlar:

* `submit(chain, values, channel_id)` hemen döner ve artan bir `job_id`
  verir; bu id o andan itibaren "en güncel"dir.
* Bir iş bitince sonucu yalnızca `job_id` hâlâ en güncelse
  `result_ready(job_id, channel_id, ChainResult)` ile yayılır; daha yeni
  bir iş gönderilmişse eski sonuç **atılır** (`stale` sinyali).
* Hata `failed(job_id, mesaj)` ile bildirilir.

`ExportRunner` (`F3-066`) ile aynı kalıp: `QThread` alt sınıfı, `run()`
içinde iş, ayrı olay döngüsü yok.
"""

from __future__ import annotations

from functools import partial

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QObject, QThread, Signal

from sonar_analyzer.processing.chain import ChainExecutionError, ChainResult, ProcessingChain


class _DspJob(QThread):
    """Tek bir zinciri worker thread'de çalıştırır."""

    done = Signal(int, object)  # job_id, ChainResult
    error = Signal(int, str)  # job_id, mesaj

    def __init__(
        self,
        job_id: int,
        chain: ProcessingChain,
        values: NDArray[np.generic],
    ) -> None:
        super().__init__()
        self._job_id = job_id
        self._chain = chain
        # Girdiyi kopyala: çağıran diziyi değiştirse bile iş etkilenmesin.
        self._values = np.array(values, dtype=np.float64)

    def run(self) -> None:  # Qt override
        try:
            result = self._chain.run(self._values)
        except (ChainExecutionError, ValueError) as exc:
            self.error.emit(self._job_id, str(exc))
        else:
            self.done.emit(self._job_id, result)


class DspRunner(QObject):
    """DSP zincirlerini worker'da çalıştırır; yalnız en güncel sonucu yayınlar."""

    #: (job_id, channel_id, ChainResult) — yalnız en güncel iş için.
    result_ready = Signal(int, str, object)
    #: (job_id, channel_id) — sonuç geldi ama daha yeni bir iş var; atıldı.
    stale = Signal(int, str)
    #: (job_id, mesaj)
    failed = Signal(int, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._counter = 0
        self._latest_job_id = 0
        self._jobs: dict[int, _DspJob] = {}
        self._channel_ids: dict[int, str] = {}

    @property
    def latest_job_id(self) -> int:
        return self._latest_job_id

    def is_current(self, job_id: int) -> bool:
        return job_id == self._latest_job_id

    @property
    def busy(self) -> bool:
        return any(job.isRunning() for job in self._jobs.values())

    def submit(
        self,
        chain: ProcessingChain,
        values: NDArray[np.generic],
        channel_id: str = "",
    ) -> int:
        """İşi kuyruğa alır, `job_id` döndürür (hemen döner, bloklamaz)."""
        self._counter += 1
        job_id = self._counter
        self._latest_job_id = job_id
        self._channel_ids[job_id] = channel_id

        job = _DspJob(job_id, chain, values)
        job.done.connect(self._on_done)
        job.error.connect(self._on_error)
        job.finished.connect(partial(self._cleanup, job_id))
        self._jobs[job_id] = job
        job.start()
        return job_id

    def wait_all(self, timeout_ms: int = 5000) -> bool:
        """Tüm işler bitene dek bekler — testler ve kapanış için."""
        ok = True
        for job in list(self._jobs.values()):
            ok = job.wait(timeout_ms) and ok
        return ok

    # -- ic ------------------------------------------------------

    def _on_done(self, job_id: int, result: object) -> None:
        channel_id = self._channel_ids.get(job_id, "")
        if not isinstance(result, ChainResult):
            return
        if job_id == self._latest_job_id:
            self.result_ready.emit(job_id, channel_id, result)
        else:
            self.stale.emit(job_id, channel_id)

    def _on_error(self, job_id: int, message: str) -> None:
        if job_id == self._latest_job_id:
            self.failed.emit(job_id, message)

    def _cleanup(self, job_id: int) -> None:
        self._jobs.pop(job_id, None)
        self._channel_ids.pop(job_id, None)
