"""Kayıtlı dosyadan `LiveSource` üreten replay adaptörü — `F5-002`, `F5-003`.

Donanımsız geliştirme için (plan Bölüm 13: "Simülatör/replay source ile
donanımsız geliştirme olanağı sağla"): bir `RecordingRepository`'yi (dosya
veya simülasyon fark etmez) 125 ms'lik pencerelere bölüp aynı sırayla
`LivePacket` akışı üretir. Üretilen **içerik** hızdan bağımsızdır — yalnız
paketler arasındaki gerçek-zaman aralığı `speed` ile ölçeklenir; `speed=2.0`
aynı akışı yarı sürede, `speed=0.5` iki katı sürede üretir.

Bu modül `LiveSource` Protocol'ünün (`F1-017`) **ötesinde** iki ek kontrol
sunar (`pause`/`resume`/`stop`) — canlı bir donanım bağlantısının aksine bir
replay durdurulup yeniden **en baştan** başlatılabilir; bu yalnız burada
anlamlıdır, temel sözleşmenin parçası değildir.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.io.live.connection_state_machine import ConnectionStateMachine
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.repository.protocol import RecordingRepository

NS_PER_SECOND = 1_000_000_000


class FileReplaySource:
    """`RecordingRepository`'den 125 ms pencereler halinde `LivePacket` üretir.

    `connect()`/`disconnect()` `ConnectionStateMachine` üzerinden yürür
    (`F5-002`): `packets()` yalnız bağlıyken (veya toparlanıyorken) paket
    üretir, `disconnect()` çağrılınca **bir sonraki pencereden önce** durur.
    """

    def __init__(
        self,
        repository: RecordingRepository,
        *,
        speed: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        if speed <= 0:
            raise ValueError(f"speed pozitif olmali: {speed}")
        self._repository = repository
        self._speed = speed
        self._sleep = sleep
        self._clock_ns = clock_ns
        self._machine = ConnectionStateMachine()
        self._paused = False
        self._stopped = False
        self._received = 0
        self._dropped = 0
        self._last_sequence: int | None = None

    @property
    def state(self) -> ConnectionState:
        return self._machine.state

    def connect(self) -> None:
        """Zaten bağlıysa etkisizdir (`LiveSource.connect()` sözleşmesi, `F1-017`)."""
        if self._machine.state is not ConnectionState.CONNECTED:
            self._machine.request_connect()
            self._machine.established()

    def disconnect(self) -> None:
        self._machine.disconnect()

    def channels(self) -> Sequence[ChannelMetadata]:
        return self._repository.channels()

    def stats(self) -> LiveStats:
        return LiveStats(
            received_packets=self._received,
            dropped_packets=self._dropped,
            queue_depth=0,
            last_sequence_no=self._last_sequence,
        )

    def pause(self) -> None:
        """Yeni pencerelerin üretimini durdurur; `resume()` ile devam eder.

        Zaten üretilmiş/beklemede paket yoktur (senkron üretici) — duraklatma
        sırasında **hiçbir** paket yayınlanmaz (`F5-004` kabul kriteri).
        """
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        """Sürmekte olan `packets()` üretecini bir sonraki kontrolde durdurur.

        Bağlantı durumunu değiştirmez — `packets()` tekrar çağrılırsa yeni
        bir üretici **en baştan** başlar (Python üretici işlevlerinin doğal
        sonucu, ayrı bir "reset" gerekmez).
        """
        self._stopped = True

    def packets(self) -> Iterator[LivePacket]:
        """Kayıt boyunca sırayla `LivePacket` üretir; `speed`'e göre aralanır.

        Her çağrı **yeni** bir üretici döndürür ve `sequence_no`'yu `0`'dan
        başlatır — canlı bir bağlantının her yeniden bağlanışında sıra
        numarasının sıfırlanmasıyla aynı ilke.
        """
        self._stopped = False
        span = self._repository.metadata().time_range
        channel_ids = [channel.id for channel in self._repository.channels()]
        sequence_no = 0
        window_start = span.start_ns
        while window_start < span.end_ns:
            while self._paused and not self._stopped:
                self._sleep(RECORD_PERIOD_NS / NS_PER_SECOND / self._speed)
            if self._stopped or not self._machine.state.is_active:
                return
            self._sleep(RECORD_PERIOD_NS / NS_PER_SECOND / self._speed)
            if self._stopped or not self._machine.state.is_active:
                return

            window = TimeRange(window_start, min(window_start + RECORD_PERIOD_NS, span.end_ns))
            chunks = [
                chunk
                for channel_id in channel_ids
                if len(chunk := self._repository.query(channel_id, window))
            ]
            events = list(self._repository.events(window))
            packet = LivePacket(
                sequence_no=sequence_no,
                received_ns=self._clock_ns(),
                chunks=chunks,
                events=events,
            )
            self._received += 1
            self._last_sequence = sequence_no
            yield packet

            sequence_no += 1
            window_start = window.end_ns
