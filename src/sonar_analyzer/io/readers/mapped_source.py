"""Memory mapping üzerinden blok okuma — `F4-053`.

Büyük bir `.bin` kaydını incelemek için dosyayı **RAM'e kopyalamak
gerekmez**: işletim sistemi dosyayı adres alanına haritalar, yalnız
gerçekten dokunulan sayfalar belleğe gelir. `MappedSource` bunu salt
okunur bir eşleme (`mmap.ACCESS_READ`) olarak sarar ve blokları
**kopyasız** `memoryview` dilimleri hâlinde verir.

    with MappedSource(path) as source:
        block = source.block(offset, length)   # memoryview, kopya değil
        header = read_file_header_v1(block)

`memoryview` `struct.unpack_from` ve `numpy.frombuffer` ile doğrudan
çalışır (`ReadableBuffer` sözleşmesi), bu yüzden decoder'lar
değişmeden mmap üzerinde çalışır.

Sınır dışı bir blok **sessizce kırpılmaz**: `MappedSourceError` verilir.

Boş dosya bir eşleme hatası değildir: ``mmap`` sıfır baytı haritalayamaz,
ama boş bir kaynak da geçerli bir girdidir (bozuk/kesik kayıt). Bu durumda
eşleme kurulmaz, `size` 0 ve `data()` boş bir görünüm olur — böylece
"bu dosya biçim olarak bozuk" kararını **format katmanı** verir, okuyucu
değil.

Windows'ta eşlenen bir dosya, eşleme açıkken silinemez veya üzerine
yazılamaz. Bu bilinçli bir ödünçtür: kopyalamamanın bedeli, kayıt açıkken
kaynağın yerinde durmasıdır. `close()` kilidi bırakır.
"""

from __future__ import annotations

import contextlib
import mmap
from pathlib import Path
from types import TracebackType


class MappedSourceError(OSError):
    """Eşleme kurulamadı ya da istenen blok dosya sınırları dışında."""


class MappedSource:
    """Bir dosyanın salt okunur bellek eşlemesi; blokları kopyasız verir."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        try:
            self._file = self._path.open("rb")
        except OSError as exc:
            raise MappedSourceError(f"kaynak açılamadı: {self._path} ({exc})") from exc
        # Boş dosya haritalanamaz (mmap kısıtı) ama geçerli bir girdidir:
        # eşleme kurulmaz, boş bir görünüm verilir.
        self._map: mmap.mmap | None = None
        if self._path.stat().st_size == 0:
            self._view = memoryview(b"")
        else:
            try:
                self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            except (OSError, ValueError) as exc:
                self._file.close()
                raise MappedSourceError(f"kaynak haritalanamadı: {self._path} ({exc})") from exc
            self._view = memoryview(self._map)
        self._closed = False

    # -- yaşam döngüsü -----------------------------------------------------

    def __enter__(self) -> MappedSource:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Eşlemeyi ve dosya tanıtıcısını bırakır (yeniden çağrılabilir).

        Bir tüketici hâlâ `block()` görünümü tutuyorsa işletim sistemi
        eşlemesi **o görünüm bırakılana kadar** yaşar; `close()` yine de
        hata vermez. Bırakılan blok geçerli kalır — kapanış, elde tutulan
        veriyi ayağının altından çekmez.
        """
        if self._closed:
            return
        self._closed = True
        self._view.release()
        if self._map is not None:
            # Dışarıda blok görünümü varsa eşleme son görünümle serbest kalır.
            with contextlib.suppress(BufferError):
                self._map.close()
        self._file.close()

    @property
    def closed(self) -> bool:
        return self._closed

    # -- sorgular ----------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    @property
    def size(self) -> int:
        """Eşlenen dosyanın bayt uzunluğu (boş dosyada 0)."""
        self._ensure_open()
        return len(self._view)

    def __len__(self) -> int:
        return self.size

    def data(self) -> memoryview:
        """Dosyanın tamamı üzerinde **kopyasız** görünüm."""
        self._ensure_open()
        return self._view

    def block(self, offset: int, length: int) -> memoryview:
        """`[offset, offset + length)` bloğu üzerinde **kopyasız** görünüm.

        Blok dosya sınırlarını aşarsa `MappedSourceError` yükseltilir —
        eksik veri sessizce kısaltılmaz.
        """
        self._ensure_open()
        if offset < 0:
            raise MappedSourceError(f"blok başlangıcı negatif olamaz: {offset}")
        if length < 0:
            raise MappedSourceError(f"blok uzunluğu negatif olamaz: {length}")
        end = offset + length
        total = len(self._view)
        if end > total:
            raise MappedSourceError(f"blok dosya sonunu aşıyor: [{offset}, {end}) > {total} bayt")
        return self._view[offset:end]

    def _ensure_open(self) -> None:
        if self._closed:
            raise MappedSourceError(f"kaynak kapatıldı: {self._path}")
