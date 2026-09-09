"""Dosya yükleme worker'ı — `F3-002`.

Plan Bölüm 10.1: *"Uzun hesaplamalar GUI thread'inde çalışmaz."* Bir `.bin`
kaydını açmak dosyanın tamamını okur, indeks üretir veya doğrular; 1 saatlik
bir dosyada bu yüz milisaniyeler, büyük bir dosyada saniyeler sürer. GUI
thread'inde yapılırsa pencere o süre boyunca donar.

Bu modül yüklemeyi ayrı bir `QThread`'e taşır:

    GUI thread            worker thread
    ----------            -------------
    submit(paths)  --->   her yol icin loader(path)
    file_loaded    <---   FileLoadResult (basari veya hata)
    finished       <---   istek bitti

`FileLoadService` GUI tarafındaki yüzdür; worker nesnesi thread'e taşınır ve
sinyaller kuyruklu bağlantıyla döner. Kayıt açma işi `loader` çağrısıyla
dışarıdan verilebilir — testler yavaş veya hata veren bir yükleyici koyabilir.

**İstek kimliği** her `submit()` çağrısında artar. `F3-004` eski isteğin
sonucunu bu kimlikle eleyecek; worker sonucu üretmeye devam etse bile GUI
hangi isteğe ait olduğunu bilir.

**Thread yaşam döngüsü — boşta thread çalışmaz.** Thread kurucuda
başlatılmaz; ilk `submit()` ile başlar ve son istek bitince `shutdown()` ile
durur. Sebep somut: thread sürekli çalışsaydı, `close()` çağrılmadan çöpe
giden her `MainWindow` "QThread: Destroyed while thread is still running"
ile süreci **çökertirdi** (Windows'ta `0xC0000409`). Bu bir kez yaşandı ve
GUI test paketinin tamamını düşürdü; lazy başlatma o sınıfı tamamen
kapatıyor. Açma işlemi kullanıcı eylemi olduğu için thread başlatma
maliyeti (< 1 ms) önemsizdir.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from sonar_analyzer.repository.file_repository import FileRecordingRepository

#: Bir yolu açıp repository döndüren çağrı; testler yerine geçebilir.
LoaderCallable = Callable[[Path], FileRecordingRepository]


def default_loader(path: Path) -> FileRecordingRepository:
    """Gerçek yükleyici: dosyayı açar ve repository'yi döndürür."""
    repository = FileRecordingRepository()
    repository.open(path)
    return repository


@dataclass(frozen=True)
class FileLoadRequest:
    """Tek bir açma talebi; birden fazla dosya içerebilir (`F3-001`)."""

    request_id: int
    paths: tuple[Path, ...]


@dataclass(frozen=True)
class FileLoadResult:
    """Tek bir dosyanın sonucu — başarı ya da **yutulmamış** hata."""

    request_id: int
    path: Path
    repository: FileRecordingRepository | None = None
    error: str = ""
    #: Teşhis için hatanın tipi; kullanıcı mesajı `F3-006`'da biçimlenecek.
    error_type: str = ""

    @property
    def succeeded(self) -> bool:
        return self.repository is not None


def _empty_id_set() -> set[int]:
    return set()


@dataclass
class _WorkerState:
    """Worker'ın iptal bayrağı; `F3-003` bunu kullanacak."""

    cancelled_requests: set[int] = field(default_factory=_empty_id_set)


class FileLoadWorker(QObject):
    """Worker thread'inde çalışan yükleyici. GUI'ye yalnız sinyalle konuşur."""

    file_loaded = Signal(object)
    request_finished = Signal(int)

    def __init__(self, loader: LoaderCallable, state: _WorkerState) -> None:
        super().__init__()
        self._loader = loader
        self._state = state

    def load(self, request: FileLoadRequest) -> None:
        """Talepteki her dosyayı sırayla açar; hata bir dosyayı atlar, diğerleri sürer.

        Bir dosyanın açılamaması tüm isteği düşürmez (`fixture-corrupt.md`
        §0 fail-soft ilkesinin GUI karşılığı): hatalı dosya `error` ile
        raporlanır, kalanlar yüklenmeye devam eder.
        """
        for path in request.paths:
            if request.request_id in self._state.cancelled_requests:
                break
            try:
                repository = self._loader(path)
            except Exception as exc:
                self.file_loaded.emit(
                    FileLoadResult(
                        request_id=request.request_id,
                        path=path,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                )
                continue
            self.file_loaded.emit(
                FileLoadResult(request_id=request.request_id, path=path, repository=repository)
            )
        self.request_finished.emit(request.request_id)


class FileLoadService(QObject):
    """GUI tarafındaki yüz: worker thread'ini kurar ve isteği ona iletir."""

    #: Worker'dan gelen tek dosya sonucu (`FileLoadResult`).
    file_loaded = Signal(object)
    #: Bir isteğin tüm dosyaları bitti (`request_id`).
    request_finished = Signal(int)
    #: Yeni bir istek başlatıldı (`request_id`) — ilerleme göstergesi için.
    request_started = Signal(int)

    _submit_requested = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        loader: LoaderCallable | None = None,
    ) -> None:
        super().__init__(parent)
        self._state = _WorkerState()
        self._next_request_id = 0
        self._pending_requests = 0

        self._thread = QThread()
        self._thread.setObjectName("file-loader")
        self._worker = FileLoadWorker(loader or default_loader, self._state)
        self._worker.moveToThread(self._thread)

        # Kuyruklu baglanti: `load` worker thread'inde calisir, sinyaller
        # GUI thread'ine geri doner.
        self._submit_requested.connect(self._worker.load)
        self._worker.file_loaded.connect(self.file_loaded)
        self._worker.request_finished.connect(self._on_worker_finished)
        # Thread BURADA baslatilmaz; bkz. `submit()` ve sinif docstring'i.

    @property
    def is_running(self) -> bool:
        """Worker thread'i ayakta mı — kapanış doğrulaması için."""
        return self._thread.isRunning()

    @property
    def last_request_id(self) -> int:
        """En son verilen istek kimliği; hiç istek yoksa `0`."""
        return self._next_request_id

    def submit(self, paths: Sequence[Path]) -> int:
        """Yükleme isteğini worker'a verir ve istek kimliğini döner.

        GUI thread'i **bloklanmaz**: çağrı hemen döner, dosyalar arka planda
        açılır (kabul kriteri).
        """
        self._next_request_id += 1
        request = FileLoadRequest(self._next_request_id, tuple(paths))
        self._pending_requests += 1
        if not self._thread.isRunning():
            self._thread.start()
        self.request_started.emit(request.request_id)
        self._submit_requested.emit(request)
        return request.request_id

    def _on_worker_finished(self, request_id: int) -> None:
        """İstek bitti: dinleyicilere haber verilir, boşta kalan thread durdurulur."""
        self._pending_requests = max(0, self._pending_requests - 1)
        self.request_finished.emit(request_id)
        if self._pending_requests == 0:
            self.shutdown()

    def cancel(self, request_id: int) -> None:
        """İsteği iptal eder; worker sıradaki dosyaya geçmeden durur (`F3-003`)."""
        self._state.cancelled_requests.add(request_id)

    def is_cancelled(self, request_id: int) -> bool:
        return request_id in self._state.cancelled_requests

    def shutdown(self, timeout_ms: int = 5_000) -> None:
        """Worker thread'ini düzgün durdurur; pencere kapanışında çağrılır."""
        if not self._thread.isRunning():
            return
        self._thread.quit()
        if not self._thread.wait(timeout_ms):  # pragma: no cover - takilan thread
            self._thread.terminate()
            self._thread.wait()
