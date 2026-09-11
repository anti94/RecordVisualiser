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

Yazma hatası olduğunda worker durur, hata metni ve `errno`'su okunabilir
kalır. Bunun bir **kayıt durumuna** (ve kullanıcıya verilen mesaja)
dönüşmesi `recording/session.py`'nin işidir (`F5-030`).

`F5-029` — flush ve güvenli kapatma
-----------------------------------

Kabul: **Stop sonrası bütün tam kayıtlar yeniden okunabilir.** Bu iki şey
gerektirir ve ikisi de `close()` içinde sırayla yapılır:

1. Kuyrukta bekleyen bloklar diske **iner** (worker durur, kalanı boşaltır,
   ardından `flush` + `fsync`). Aksi hâlde son saniyelerin kaydı işletim
   sistemi tamponunda kalıp kaybolabilirdi.
2. Dosyanın sonunda kayıt sınırına oturmayan **yarım blok kalmaz**. Bir
   yazma ortasında kesilirse (disk dolu) o artık baytlar kesilir ve
   `truncated_bytes` ile görünür kalır — okuyucu tarafında bozuk bir kayıt
   gibi görünmeleri, tam kayıtların da okunamaz sanılmasına yol açardı.

`flush()` ise dosyayı **kapatmadan** bir ara noktayı diske indirir; kayıt
sürerken çağrılabilir.
"""

from __future__ import annotations

import os
import threading
import time
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
        self._written_bytes = 0
        self._error: str | None = None
        self._error_code: int | None = None

    @property
    def written_records(self) -> int:
        return self._written

    @property
    def written_bytes(self) -> int:
        """**Tamamı** yazılmış blokların toplam uzunluğu — `F5-029`.

        Sayaç yalnız `write()` hatasız döndükten sonra artar; yarım kalan
        bir blok buraya sayılmaz, böylece dosyanın güvenli sonu bilinir.
        """
        return self._written_bytes

    @property
    def error(self) -> str | None:
        """Yazma sırasında oluşan hata; yoksa `None`."""
        return self._error

    @property
    def error_code(self) -> int | None:
        """Hatanın `errno` değeri — `ENOSPC` gibi durumları ayırt etmek için (`F5-030`)."""
        return self._error_code

    def _record_failure(self, exc: OSError) -> None:
        self._error = f"{exc}"
        self._error_code = exc.errno

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
                self._record_failure(exc)
                break
            self._written += 1
            self._written_bytes += len(block)

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
                self._record_failure(exc)
                return
            self._written += 1
            self._written_bytes += len(block)


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
        self._header_bytes = 0
        self._truncated_bytes = 0

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
    def error_code(self) -> int | None:
        """Yazma hatasının `errno` değeri; yoksa `None` (`F5-030`)."""
        worker = self._worker
        return None if worker is None else worker.error_code

    @property
    def is_open(self) -> bool:
        return self._stream is not None

    @property
    def committed_bytes(self) -> int:
        """Dosyanın **güvenli** uzunluğu: başlık + tamamı yazılmış bloklar."""
        worker = self._worker
        return self._header_bytes + (0 if worker is None else worker.written_bytes)

    @property
    def truncated_bytes(self) -> int:
        """Kapatılırken atılan yarım blok baytı — normalde `0`, kayıp görünürdür."""
        return self._truncated_bytes

    def open(self, header: bytes) -> None:
        """Dosyayı açar, başlığı **doğrudan** yazar ve worker'ı başlatır.

        Başlık kuyruğa girmez: dosyanın ilk baytı olmalı ve kuyruk taşması
        yüzünden düşmesi dosyayı okunamaz kılardı.
        """
        if self._stream is not None:
            raise RuntimeError("Kayit zaten acik")
        if self._worker is not None:
            # Kuyruk kapatildi; ayni yazici ikinci bir dosya acamaz. Dosya
            # degistirme (`F5-031`) yeni bir RecordingWriter ile yapilir.
            raise RuntimeError("Kapatilan kayit yeniden acilamaz")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        stream = self._open_stream(self._path)
        stream.write(header)
        self._header_bytes = len(header)
        self._truncated_bytes = 0
        self._stream = stream
        self._worker = DiskWriterWorker(stream, self._queue)
        self._worker.start()

    def submit(self, block: bytes) -> bool:
        """Bir kayıt bloğunu kuyruğa koyar; **beklemez**."""
        if self._stream is None:
            raise RuntimeError("Once open() cagrilmali")
        return self._queue.submit(block)

    def flush(self, *, timeout_s: float = 5.0) -> bool:
        """Kuyruktakiler diske yazılana kadar bekler — `F5-029`.

        Dosya **açık kalır**; kayıt sürerken bir ara noktanın diske
        indiğinden emin olmak için kullanılır. Süre dolarsa `False` döner
        (bloklar hâlâ yoldadır) — sessizce "tamam" denmez.

        Beklenen ölçü kuyruk derinliği **değil**, yazılan blok sayısıdır:
        worker bir bloğu kuyruktan aldığı anda derinlik sıfırlanır ama blok
        henüz diske inmemiştir; derinliğe bakmak son kaydı ıskalardı.
        """
        if self._stream is None:
            return True
        target = self._queue.accepted_records
        deadline = time.monotonic() + timeout_s
        while self.written_records < target:
            if self.error is not None or time.monotonic() > deadline:
                return False
            time.sleep(0.005)
        self._sync(self._stream)
        return self.error is None

    def close(self, *, wait_ms: int = 5000) -> None:
        """Worker'ı durdurur, kalanları yazdırır ve dosyayı **güvenle** kapatır.

        `F5-029` garantisi: bu çağrı döndükten sonra dosyadaki bütün **tam**
        kayıtlar yeniden okunabilir. Sıra önemlidir — önce worker biter
        (kuyrukta kalan bloklar yazılır), sonra akış diske senkronlanır,
        en son dosya kapanır. Ters sırada yarım bir kayıt kalabilirdi.
        """
        worker, stream = self._worker, self._stream
        if worker is not None:
            worker.stop()
            worker.join(timeout=wait_ms / 1000)
            self._worker = worker  # hata/sayac okunabilsin diye korunur
        if stream is not None:
            self._discard_partial_tail(stream)
            self._sync(stream)
            stream.close()
        self._stream = None

    def _discard_partial_tail(self, stream: BinaryIO) -> None:
        """Kayıt sınırına oturmayan son baytları atar — `F5-029`.

        Bir blok yazılırken kesilirse (disk dolu, `F5-030`) dosyanın sonunda
        yarım bir kayıt kalır. Okuyucu onu bozuk bir kayıt olarak görür ve
        dosyanın tamamından şüphe edilirdi; burada kesilip `truncated_bytes`
        ile duyurulur — sessizce atılmaz.
        """
        safe_end = self.committed_bytes
        try:
            stream.flush()
            size = os.fstat(stream.fileno()).st_size
        except (OSError, AttributeError, ValueError):
            return
        if size <= safe_end:
            return
        try:
            stream.truncate(safe_end)
        except (OSError, AttributeError, ValueError):  # pragma: no cover - nadir akis turu
            return
        self._truncated_bytes = size - safe_end

    def _sync(self, stream: BinaryIO) -> None:
        """Akışı ve (mümkünse) işletim sistemi tamponunu diske indirir.

        `fsync` her akış türünde bulunmaz (testlerdeki sarmalayıcılar
        gibi); bulunmaması bir hata değildir, o zaman `flush` yeterlidir.
        """
        try:
            stream.flush()
            fileno = stream.fileno()
        except (OSError, AttributeError, ValueError):
            return
        try:
            os.fsync(fileno)
        except OSError:  # pragma: no cover - dosya sistemi destegi yoksa
            return
