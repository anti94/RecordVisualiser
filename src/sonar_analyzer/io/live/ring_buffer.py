"""Sabit kapasiteli canlı veri halka tamponu — `F5-014`.

Plan Bölüm 13: "Sabit boyutlu ring buffer" ve Bölüm 11.2: "LRU cache ve
açık bellek bütçesi". Buradaki sözleşme tek cümle: **bellek üst sınırı
baştan bellidir ve hiç büyümez.** Diziler kurulumda bir kez ayrılır;
sonsuz akış da gelse `nbytes` değişmez (`tests/unit/test_ring_buffer.py`
bunu 100 kapasite katı veri yazarak ölçüyor).

Kapasite aşılınca çıkarma politikası **tanımlıdır**: en eski örnek önce
düşer (FIFO). Belirsiz/rastgele bir çıkarma, kullanıcının grafikte hangi
verinin kaybolduğunu bilememesi demek olurdu.

Zaman penceresine göre sorgulama `F5-015`'in işidir; bu modül yalnız
yazma, çıkarma ve sıra koruma sorumluluğunu taşır.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.downsampling import downsample_chunk
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.live.protocol import LivePacket


def _in_time_order(chunk: DataChunk) -> DataChunk:
    """Zaman sırasına sokar; zaten sıralıysa **kopyalamaz**.

    Geç gelen paketler (`F5-012`'nin `out_of_order` sınıfı) tampona yazılma
    sırasıyla girer; sorgu sonucunun sırası yazılma sırasına değil **zamana**
    bağlı olmalıdır. Kararlı (`stable`) sıralama, eşit zaman damgalı
    örneklerin göreli sırasını korur.
    """
    if chunk.is_monotonic:
        return chunk
    order = np.argsort(chunk.timestamps_ns, kind="stable")
    return DataChunk(
        channel_id=chunk.channel_id,
        timestamps_ns=chunk.timestamps_ns[order],
        values=chunk.values[order],
        quality=None if chunk.quality is None else chunk.quality[order],
    )


class ChannelRing:
    """Tek kanalın sabit kapasiteli halka tamponu."""

    def __init__(self, channel_id: str, capacity: int, *, with_quality: bool = True) -> None:
        if capacity < 1:
            raise ValueError(f"capacity pozitif olmali: {capacity}")
        self._channel_id = channel_id
        self._capacity = capacity
        self._timestamps: NDArray[np.int64] = np.zeros(capacity, dtype=np.int64)
        self._values: NDArray[np.float64] = np.zeros(capacity, dtype=np.float64)
        self._quality: NDArray[np.uint8] | None = (
            np.zeros(capacity, dtype=np.uint8) if with_quality else None
        )
        self._start = 0
        self._count = 0

    @property
    def channel_id(self) -> str:
        return self._channel_id

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def count(self) -> int:
        return self._count

    @property
    def nbytes(self) -> int:
        """Ölçülen bellek — kurulumdan sonra **hiç değişmez**."""
        quality = 0 if self._quality is None else int(self._quality.nbytes)
        return int(self._timestamps.nbytes + self._values.nbytes) + quality

    def append(
        self,
        timestamps: NDArray[np.int64],
        values: NDArray[np.generic],
        quality: NDArray[np.uint8] | None = None,
    ) -> int:
        """Örnekleri yazar; **çıkarılan** (düşen) örnek sayısını döndürür."""
        total = int(timestamps.shape[0])
        if total == 0:
            return 0
        if total != int(values.shape[0]):
            raise ValueError(
                f"{self._channel_id}: zaman ({total}) ve deger ({values.shape[0]}) "
                "uzunluklari farkli"
            )

        if total >= self._capacity:
            # Tek parca kapasiteden buyuk: yalniz SON `capacity` ornek sigar.
            evicted = self._count + (total - self._capacity)
            self._timestamps[:] = timestamps[-self._capacity :]
            self._values[:] = values[-self._capacity :]
            if self._quality is not None:
                if quality is None:
                    self._quality[:] = 0
                else:
                    self._quality[:] = quality[-self._capacity :]
            self._start = 0
            self._count = self._capacity
            return evicted

        free = self._capacity - self._count
        evicted = max(0, total - free)
        write_at = (self._start + self._count) % self._capacity
        head = min(total, self._capacity - write_at)

        self._timestamps[write_at : write_at + head] = timestamps[:head]
        self._values[write_at : write_at + head] = values[:head]
        if self._quality is not None:
            self._quality[write_at : write_at + head] = 0 if quality is None else quality[:head]

        tail = total - head
        if tail:
            self._timestamps[:tail] = timestamps[head:]
            self._values[:tail] = values[head:]
            if self._quality is not None:
                self._quality[:tail] = 0 if quality is None else quality[head:]

        self._count = min(self._capacity, self._count + total)
        if evicted:
            self._start = (self._start + evicted) % self._capacity
        return evicted

    def snapshot(self) -> DataChunk:
        """Tampondaki örnekleri **yazılma sırasıyla** (en eskiden en yeniye) verir."""
        if self._count == 0:
            return DataChunk.empty(self._channel_id, dtype="float64")
        indices = (self._start + np.arange(self._count, dtype=np.int64)) % self._capacity
        return DataChunk(
            channel_id=self._channel_id,
            timestamps_ns=self._timestamps[indices].copy(),
            values=self._values[indices].copy(),
            quality=None if self._quality is None else self._quality[indices].copy(),
        )

    def clear(self) -> None:
        self._start = 0
        self._count = 0


class LiveRingBuffer:
    """Kanal başına `ChannelRing` tutan, bellek üst sınırı belli canlı tampon."""

    def __init__(self, capacity_samples: int, *, with_quality: bool = True) -> None:
        if capacity_samples < 1:
            raise ValueError(f"capacity_samples pozitif olmali: {capacity_samples}")
        self._capacity = capacity_samples
        self._with_quality = with_quality
        self._rings: dict[str, ChannelRing] = {}
        self._evicted_total = 0

    @property
    def capacity_samples(self) -> int:
        return self._capacity

    @property
    def evicted_total(self) -> int:
        """Oturum boyunca çıkarılan toplam örnek — kullanıcıya "veri düştü" demek için."""
        return self._evicted_total

    @property
    def nbytes(self) -> int:
        """Tüm kanalların ölçülen toplam belleği; kanal sayısı sabitken sabittir."""
        return sum(ring.nbytes for ring in self._rings.values())

    def channels(self) -> tuple[str, ...]:
        return tuple(sorted(self._rings))

    def count(self, channel_id: str) -> int:
        ring = self._rings.get(channel_id)
        return 0 if ring is None else ring.count

    def append_chunk(self, chunk: DataChunk) -> int:
        """Bir kanalın örneklerini yazar; çıkarılan örnek sayısını döndürür."""
        ring = self._rings.get(chunk.channel_id)
        if ring is None:
            ring = ChannelRing(chunk.channel_id, self._capacity, with_quality=self._with_quality)
            self._rings[chunk.channel_id] = ring
        evicted = ring.append(chunk.timestamps_ns, chunk.values, chunk.quality)
        self._evicted_total += evicted
        return evicted

    def append_packet(self, packet: LivePacket) -> int:
        """Bir `LivePacket`'in bütün kanallarını yazar; toplam çıkarmayı döndürür."""
        return sum(self.append_chunk(chunk) for chunk in packet.chunks)

    def snapshot(self, channel_id: str) -> DataChunk:
        ring = self._rings.get(channel_id)
        if ring is None:
            return DataChunk.empty(channel_id, dtype="float64")
        return ring.snapshot()

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        """Seçili aralıktaki örnekler, **her zaman zaman sırasında** — `F5-015`.

        İmza `RecordingRepository.query()` ile birebir aynıdır: canlı tampon
        da kayıtlı dosyayla aynı gösterim boru hattını besleyebilsin diye
        (plan Bölüm 7.4: "Kayıtlı dosya ve canlı akış aynı sözleşmeyi
        karşılar").

        Aralık yarı-açıktır (`[start_ns, end_ns)`, `TimeRange` sözleşmesi).
        Halka sarılmış olsa da, araya geç gelen (`F5-012` `out_of_order`)
        örnekler yazılmış olsa da sonuç zamana göre sıralıdır. Aralıkta veri
        yoksa **boş ama geçerli** bir `DataChunk` döner.
        """
        snapshot = self.snapshot(channel_id)
        if len(snapshot) == 0:
            return snapshot

        ordered = _in_time_order(snapshot)
        start = int(np.searchsorted(ordered.timestamps_ns, time_range.start_ns, side="left"))
        stop = int(np.searchsorted(ordered.timestamps_ns, time_range.end_ns, side="left"))
        flags = ordered.quality
        selected = DataChunk(
            channel_id=ordered.channel_id,
            timestamps_ns=np.ascontiguousarray(ordered.timestamps_ns[start:stop]),
            values=np.ascontiguousarray(ordered.values[start:stop]),
            quality=None if flags is None else np.ascontiguousarray(flags[start:stop]),
        )
        return downsample_chunk(selected, max_points)

    def time_span(self, channel_id: str) -> TimeRange | None:
        """Tamponun şu an kapsadığı aralık; boşsa `None`.

        Bitiş, son örnekten **bir ns sonrasıdır**: `TimeRange` yarı-açık
        olduğu için `query(time_span(...))` son örneği de kapsar.
        """
        ordered = _in_time_order(self.snapshot(channel_id))
        if len(ordered) == 0:
            return None
        return TimeRange(int(ordered.timestamps_ns[0]), int(ordered.timestamps_ns[-1]) + 1)

    def clear(self) -> None:
        for ring in self._rings.values():
            ring.clear()
        self._evicted_total = 0
