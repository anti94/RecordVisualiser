"""Büyük dışa aktarma için worker ve iptal — `F3-066`.

Plan Bölüm 10.1: *"Uzun hesaplamalar GUI thread'inde çalışmaz."* Bir
kanalın tüm kaydını CSV'ye dökmek milyonlarca satır olabilir; GUI
thread'inde yapılırsa pencere o süre boyunca donar.

`ExportRunner` bir `QThread`'tir; `run()` içinde işi çalıştırır (ayrı
bir olay döngüsü yok — iş bitince thread biter):

    GUI thread              worker thread (run)
    ----------              -------------------
    start()      ------->   job(should_cancel, on_progress)
    progress     <-------   (yazılan, toplam)
    export_finished <----   sonuç (başarı)
    cancelled    <-------   ExportCancelled yakalandı
    failed       <-------   ValueError / OSError mesajı

`cancel()` yalnız bir bayrak set eder; `job` bunu her satırda yoklar ve
`ExportCancelled` fırlatır. `csv_export.write_channel_csv` atomik yazdığı
için iptal edilen dosya **hedefte hiç oluşmaz** — yarım dosya
tamamlanmış gibi sunulmaz.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from sonar_analyzer.export.csv_export import ExportCancelled

#: `job(should_cancel, on_progress) -> sonuç`. `should_cancel()` True ise
#: job `ExportCancelled` fırlatmalıdır.
ExportJob = Callable[[Callable[[], bool], Callable[[int, int], None]], object]


class ExportRunner(QThread):
    """Bir dışa aktarma işini worker thread'de çalıştırır; iptal edilebilir."""

    #: Yazılan / toplam satır.
    progress = Signal(int, int)
    #: İş başarıyla bitti; yük = job'un sonucu (ör. `CsvExportResult`).
    #: (`QThread.finished` ile çakışmasın diye `export_finished`.)
    export_finished = Signal(object)
    #: Kullanıcı iptal etti; hedef dosya oluşmadı.
    cancelled = Signal()
    #: İş hata verdi; yük = mesaj.
    failed = Signal(str)

    def __init__(self, job: ExportJob) -> None:
        super().__init__()
        self._job = job
        self._cancel_requested = False

    # -- GUI thread'inden çağrılır -----------------------------------

    def cancel(self) -> None:
        """İptal ister; job bir sonraki satır yoklamasında durur."""
        self._cancel_requested = True

    @property
    def is_running(self) -> bool:
        return self.isRunning()

    def wait_done(self, timeout_ms: int = 5000) -> bool:
        """Thread bitene dek bekler — testler ve kapanış için."""
        return self.wait(timeout_ms)

    # -- worker thread -------------------------------------------

    def run(self) -> None:  # Qt override
        try:
            result = self._job(lambda: self._cancel_requested, self.progress.emit)
        except ExportCancelled:
            self.cancelled.emit()
        except (ValueError, OSError) as exc:
            self.failed.emit(str(exc))
        else:
            self.export_finished.emit(result)
