"""DSP işlerini worker üzerinden çalıştır, iptal + eski sonuç denetimi —
`F4-003`, `F4-004`.

Bir `ProcessingChain.run()` büyük bir kanalda milyonlarca örnek üzerinde
çalışabilir; GUI thread'inde yapılırsa pencere donar. `DspRunner` her
işi kısa ömürlü bir `QThread`'e taşır ve **yalnız uygulanabilir** işin
sonucunu yayınlar.

Bir sonucun grafiğe **uygulanabilir** olması için üç koşul birden:

1. Daha yeni bir iş gönderilmemiş olmalı (`job_id == latest_job_id`).
2. İş ait olduğu **seçim anahtarına** hâlâ bağlı olmalı; seçim
   `set_selection(key)` ile değiştiyse eski işlerin sonucu düşer.
3. İş **iptal edilmemiş** olmalı (`cancel` / `cancel_all`).

Aksi hâlde sonuç `stale` (eski) ya da `cancelled` (iptal) sinyaliyle
bildirilir ve `result_ready` **yayılmaz** — çağıran grafiğe uygulamaz.

`ExportRunner` (`F3-066`) ile aynı kalıp: `QThread` alt sınıfı, `run()`
içinde iş, ayrı olay döngüsü yok. Zincir tek NumPy geçişi olduğu için
iptal **kooperatiftir**: iş sonuna kadar koşar ama sonucu bastırılır.
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
    """DSP zincirlerini worker'da çalıştırır; iptal ve eski sonuçları eler."""

    #: (job_id, channel_id, ChainResult) — yalnız uygulanabilir iş için.
    result_ready = Signal(int, str, object)
    #: (job_id, channel_id) — sonuç geldi ama daha yeni iş / seçim var; atıldı.
    stale = Signal(int, str)
    #: (job_id, channel_id) — iş kullanıcı tarafından iptal edildi.
    cancelled = Signal(int, str)
    #: (job_id, mesaj)
    failed = Signal(int, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._counter = 0
        self._latest_job_id = 0
        self._selection = ""
        self._jobs: dict[int, _DspJob] = {}
        self._channel_ids: dict[int, str] = {}
        self._job_selection: dict[int, str] = {}
        self._cancelled: set[int] = set()

    # -- sorgular ----------------------------------------------

    @property
    def latest_job_id(self) -> int:
        return self._latest_job_id

    @property
    def selection(self) -> str:
        return self._selection

    def is_current(self, job_id: int) -> bool:
        """`job_id` sonucu grafiğe uygulanabilir mi (yeni değil, seçim aynı, iptal değil)."""
        if job_id != self._latest_job_id or job_id in self._cancelled:
            return False
        bound = self._job_selection.get(job_id)
        # İşin bağlandığı seçim kaydı yoksa (hiç görülmemiş id) güncel sayılmaz.
        return bound is not None and bound == self._selection

    @property
    def busy(self) -> bool:
        return any(job.isRunning() for job in self._jobs.values())

    # -- seçim / iptal --------------------------------------

    def set_selection(self, key: str) -> None:
        """Etkin seçimi değiştirir; farklı seçime bağlı işlerin sonucu düşer — `F4-004`."""
        self._selection = key

    def cancel(self, job_id: int) -> None:
        """Tek bir işi iptal eder; sonucu grafiğe uygulanmaz — `F4-004`."""
        self._cancelled.add(job_id)

    def cancel_all(self) -> None:
        """Uçuştaki tüm işleri iptal eder."""
        self._cancelled.update(self._jobs)

    # -- gönderim --------------------------------------------

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
        self._job_selection[job_id] = self._selection

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
        if job_id in self._cancelled:
            self.cancelled.emit(job_id, channel_id)
        elif self.is_current(job_id):
            self.result_ready.emit(job_id, channel_id, result)
        else:
            self.stale.emit(job_id, channel_id)

    def _on_error(self, job_id: int, message: str) -> None:
        if job_id in self._cancelled:
            self.cancelled.emit(job_id, self._channel_ids.get(job_id, ""))
        elif self.is_current(job_id):
            self.failed.emit(job_id, message)

    def _cleanup(self, job_id: int) -> None:
        self._jobs.pop(job_id, None)
        self._channel_ids.pop(job_id, None)
        self._cancelled.discard(job_id)
        # `_job_selection` bilerek korunur: iş bittikten sonra da
        # `is_current(job_id)` seçimin değişip değişmediğini bilebilmeli.
