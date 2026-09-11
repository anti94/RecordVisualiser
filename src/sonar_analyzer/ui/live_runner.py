"""Canlı akışı grafiklere bağlayan worker — `F5-022`.

Kabul kriterinin ikinci yarısı ("UI thread bloklanmaz") mimariyle
sağlanır, iyi niyetle değil:

* **Worker thread** (`_LiveReader`, `QThread`) kaynağın `packets()`
  üretecini döndürür ve her paketi `BoundedPacketQueue`'ya (`F5-016`)
  koyar. Soket beklemesi, çözümleme ve CRC burada olur.
* **UI thread** kuyruğu yalnız *boşaltır*: `drain_into()` hazır paketleri
  alıp `LiveRepository`'ye (`F5-021`) yazar. Kuyruk boşsa iş yapmaz ve
  **beklemez** — bu yüzden arayüz, kaynak ne kadar yavaş olursa olsun
  duyarlı kalır.

İkisi arasındaki tek temas noktası iş parçacığı güvenli kuyruktur; UI
thread hiçbir zaman soketi okumaz, worker hiçbir zaman widget'a dokunmaz.

Yenileme sıklığı çağırana bırakılır (`F4-061`'in 20 Hz kısıtlaması gibi
bir zamanlayıcıyla sürülür); bu modül kendi `QTimer`'ını kurmaz, böylece
testler zamanlayıcı beklemeden `drain_into()`'yu doğrudan çağırabilir.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from sonar_analyzer.io.live.packet_queue import BoundedPacketQueue, DropPolicy
from sonar_analyzer.io.live.protocol import LiveSource
from sonar_analyzer.repository.live_repository import LiveRepository

DEFAULT_QUEUE_SIZE = 256


class _LiveReader(QThread):
    """Kaynağın paketlerini kuyruğa taşıyan worker; widget'a dokunmaz."""

    failed = Signal(str)
    finished_reading = Signal()

    def __init__(self, source: LiveSource, queue: BoundedPacketQueue) -> None:
        super().__init__()
        self._source = source
        self._queue = queue
        self._stopping = False

    def stop(self) -> None:
        """Okumayı kooperatif olarak durdurur (bir sonraki pakette çıkar)."""
        self._stopping = True

    def run(self) -> None:  # Qt override
        try:
            for packet in self._source.packets():
                if self._stopping:
                    break
                self._queue.put(packet)
        except Exception as exc:
            self.failed.emit(f"{exc}")
        finally:
            self.finished_reading.emit()


class LiveRunner:
    """Canlı kaynağı worker'da okur, UI tarafında kuyruğu boşaltır."""

    def __init__(
        self,
        *,
        queue_maxsize: int = DEFAULT_QUEUE_SIZE,
        policy: DropPolicy = DropPolicy.DROP_OLDEST,
    ) -> None:
        self.queue = BoundedPacketQueue(queue_maxsize, policy=policy)
        self._reader: _LiveReader | None = None

    @property
    def is_reading(self) -> bool:
        reader = self._reader
        return reader is not None and reader.isRunning()

    def start(self, source: LiveSource) -> _LiveReader:
        """Worker'ı başlatır ve okuyucuyu döndürür (sinyallere bağlanmak için)."""
        self.stop()
        reader = _LiveReader(source, self.queue)
        reader.start()
        self._reader = reader
        return reader

    def stop(self, *, wait_ms: int = 2000) -> None:
        """Worker'ı durdurur ve biteceğini bekler; kuyruk korunur."""
        reader = self._reader
        if reader is None:
            return
        reader.stop()
        if reader.isRunning():
            reader.wait(wait_ms)
        self._reader = None

    def drain_into(self, repository: LiveRepository, *, limit: int | None = None) -> int:
        """Kuyruktaki paketleri repository'ye yazar; **yazılan paket** sayısını döner.

        UI thread bu çağrıda **beklemez**: kuyruk boşsa hemen `0` döner.
        `limit` verilirse tek karede en çok o kadar paket işlenir — çok
        büyük bir birikim tek karede arayüzü meşgul etmesin diye.
        """
        written = 0
        while limit is None or written < limit:
            packet = self.queue.get()
            if packet is None:
                break
            repository.ingest(packet)
            written += 1
        return written
