"""Disk yazma kuyruğu ve worker — `F5-028`.

Kabul: **yavaş disk UI'ı kilitlemez; taşma ve kayıp görünürdür.**

Kayıt yazımı canlı akıştan bir kuyrukla ayrılır (`F5-016`'nın paket
kuyruğuyla aynı ilke, bu kez bayt blokları için):

* Üretici (canlı akışı işleyen taraf) `submit()` ile **beklemez**: kuyruk
  doluysa blok düşer ve `dropped_records` artar. Beklemek, yavaş bir
  diskin arayüzü kilitlemesi demek olurdu.
* Worker thread kuyruğu boşaltıp dosyaya yazar; `flush()`/`stop()` ile
  senkronlanır.

Kayıp **görünürdür**: düşen blok sayısı, yazılan blok sayısı ve kuyruk
derinliği okunabilir sayaçlardır. Sessizce düşen bir kayıt, kullanıcının
eksik bir dosyayı tam sanması demek olurdu.

Yazma hatalarının işlenmesi (`disk dolu` vb.) `F5-030`'un işidir; burada
hata yalnız kaydedilir ve worker durur.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

DEFAULT_QUEUE_BLOCKS = 512


def _open_binary(path: Path) -> BinaryIO:
    """Öntanımlı akış açıcı: dosyayı ikili yazma kipinde açar."""
    return path.open("wb")


class DiskWriteQueue:
    """Sınırlı, iş parçacığı güvenli bayt bloğu kuyruğu."""

    def __init__(self, maxsize: int = DEFAULT_QUEUE_BLOCKS) -> None:
        if maxsize < 1:
            raise ValueError(f"maxsize pozitif olmali: {maxsize}")
        self._maxsize = maxsize
        self._blocks: deque[bytes] = deque()
        self._condition = threading.Condition()
        self._dropped = 0
        self._accepted = 0
        self._peak_depth = 0
        self._closed = False

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def depth(self) -> int:
        with self._condition:
            return len(self._blocks)

    @property
    def peak_depth(self) -> int:
        with self._condition:
            return self._peak_depth

    @property
    def dropped_records(self) -> int:
        """Kuyruk dolu olduğu için **düşen** blok sayısı — kayıp buradan görünür."""
        with self._condition:
            return self._dropped

    @property
    def accepted_records(self) -> int:
        with self._condition:
            return self._accepted

    def submit(self, block: bytes) -> bool:
        """Bloğu kuyruğa koyar; **beklemez**. Kabul edildiyse `True`.

        Kuyruk doluysa blok düşer (`DROP_NEWEST`): kayıtta süreklilik,
        tazelikten önemlidir — baştaki kayıtları atıp sondakileri tutmak
        dosyayı ortasından delerdi.
        """
        with self._condition:
            if self._closed:
                raise RuntimeError("Kuyruk kapatildi")
            if len(self._blocks) >= self._maxsize:
                self._dropped += 1
                return False
            self._blocks.append(block)
            self._accepted += 1
            self._peak_depth = max(self._peak_depth, len(self._blocks))
            self._condition.notify_all()
            return True

    def take(self, timeout_s: float | None = None) -> bytes | None:
        """Sıradaki bloğu alır; kuyruk boş ve kapalıysa `None`."""
        with self._condition:
            if not self._blocks and not self._closed and timeout_s is not None:
                self._condition.wait_for(
                    lambda: bool(self._blocks) or self._closed, timeout=timeout_s
                )
            if not self._blocks:
                return None
            return self._blocks.popleft()

    def close(self) -> None:
        """Yeni gönderimi kapatır; kuyrukta kalanlar hâlâ alınabilir."""
        with self._condition:
            self._closed = True
            self._condition.notify_all()


class DiskWriterWorker(threading.Thread):
    """Kuyruğu boşaltıp dosyaya yazan worker; UI thread'ine dokunmaz."""

    def __init__(self, stream: BinaryIO, queue: DiskWriteQueue) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._queue = queue
        self._stopping = threading.Event()
        self._written = 0
        self._error: str | None = None

    @property
    def written_records(self) -> int:
        return self._written

    @property
    def error(self) -> str | None:
        """Yazma sırasında oluşan hata; yoksa `None` (ayrıntılı işleme `F5-030`)."""
        return self._error

    def stop(self) -> None:
        self._stopping.set()
        self._queue.close()

    def run(self) -> None:
        while not self._stopping.is_set():
            block = self._queue.take(timeout_s=0.05)
            if block is None:
                if self._queue.depth == 0 and self._stopping.is_set():
                    break
                continue
            try:
                self._stream.write(block)
            except OSError as exc:
                self._error = f"{exc}"
                break
            self._written += 1

        # Durdurulurken kuyrukta kalanlari bosalt: yarim kalan bloklar
        # sessizce kaybolmamali.
        if self._error is None:
            self._drain_remaining()

    def _drain_remaining(self) -> None:
        while True:
            block = self._queue.take()
            if block is None:
                return
            try:
                self._stream.write(block)
            except OSError as exc:
                self._error = f"{exc}"
                return
            self._written += 1


class RecordingWriter:
    """Kayıt bloklarını kuyruğa koyup worker'a yazdırır — `F5-028`."""

    def __init__(
        self,
        path: Path,
        *,
        queue_maxsize: int = DEFAULT_QUEUE_BLOCKS,
        open_stream: Callable[[Path], BinaryIO] | None = None,
    ) -> None:
        self._path = path
        self._queue = DiskWriteQueue(queue_maxsize)
        # Akisi enjekte etmek yavas/hatali diski gercek kodla test etmeyi
        # saglar (`F5-028` yavaslik, `F5-030` yazma hatasi).
        self._open_stream = open_stream if open_stream is not None else _open_binary
        self._stream: BinaryIO | None = None
        self._worker: DiskWriterWorker | None = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def queue(self) -> DiskWriteQueue:
        return self._queue

    @property
    def written_records(self) -> int:
        worker = self._worker
        return 0 if worker is None else worker.written_records

    @property
    def dropped_records(self) -> int:
        return self._queue.dropped_records

    @property
    def error(self) -> str | None:
        worker = self._worker
        return None if worker is None else worker.error

    @property
    def is_open(self) -> bool:
        return self._stream is not None

    def open(self, header: bytes) -> None:
        """Dosyayı açar, başlığı **doğrudan** yazar ve worker'ı başlatır.

        Başlık kuyruğa girmez: dosyanın ilk baytı olmalı ve kuyruk taşması
        yüzünden düşmesi dosyayı okunamaz kılardı.
        """
        if self._stream is not None:
            raise RuntimeError("Kayit zaten acik")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        stream = self._open_stream(self._path)
        stream.write(header)
        self._stream = stream
        self._worker = DiskWriterWorker(stream, self._queue)
        self._worker.start()

    def submit(self, block: bytes) -> bool:
        """Bir kayıt bloğunu kuyruğa koyar; **beklemez**."""
        if self._stream is None:
            raise RuntimeError("Once open() cagrilmali")
        return self._queue.submit(block)

    def close(self, *, wait_ms: int = 5000) -> None:
        """Worker'ı durdurur, kalanları yazdırır ve dosyayı kapatır."""
        worker, stream = self._worker, self._stream
        if worker is not None:
            worker.stop()
            worker.join(timeout=wait_ms / 1000)
            self._worker = worker  # hata/sayac okunabilsin diye korunur
        if stream is not None:
            stream.flush()
            stream.close()
        self._stream = None
