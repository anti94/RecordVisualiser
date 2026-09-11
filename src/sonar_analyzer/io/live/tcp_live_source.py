"""TCP tabanlı tam `LiveSource` — `F5-008`.

`TcpConnection`'ın (`F5-007`) ham bayt akışını `wire_header`/`payload_codec`
(`F5-006`) ile birleştirir. UDP'nin aksine parçalama yok — TCP'de
`fragment_count` her zaman `1`'dir (`docs/live/protocol-contract.md` §3.2)
— ama çerçeve sınırı da yok: bir `recv()` bir çerçeveye denk gelmez.

Bu modül kendi bayt tamponunda biriktirir: **bölünmüş** bir çerçeve
tamamlanana kadar beklenir, **aynı okumada** gelen birden çok çerçeve
sırayla ve **tam bir kez** çözülür. Tanınmayan bir başlık akış senkronunu
bozduğu için (UDP'nin aksine "bir sonraki datagram"a geçilemez — akış
tektir) yeniden eşitleme yoktur; bu durum diyagnostiğe yazılır ve
bağlantı kapatılır (Serial'in `SYNC` ile yeniden eşitlemesi ayrı bir
protokol özelliğidir, TCP'de karşılığı yok).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.time_base import TimeBase
from sonar_analyzer.io.live.live_time import TimedWindow, timed_window_from_packet
from sonar_analyzer.io.live.payload_codec import decode_payload
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.io.live.tcp_connection import TcpConnection
from sonar_analyzer.io.live.wire_header import (
    TruncatedDatagramError,
    UnrecognizedFrameError,
    peek_frame_length,
    unpack_frame,
)


class TcpLiveSource:
    """`LiveSource` sözleşmesini TCP tel protokolü üzerinden karşılar."""

    def __init__(
        self,
        connection: TcpConnection,
        *,
        channels: Sequence[ChannelMetadata] = (),
        clock_ns: Callable[[], int] = time.time_ns,
        time_base: TimeBase | None = None,
        ticks0: int = 0,
    ) -> None:
        self._connection = connection
        self._channels = tuple(channels)
        self._clock_ns = clock_ns
        self._time_base = time_base
        self._ticks0 = ticks0
        self._received = 0
        self._dropped = 0
        self._truncated = 0
        self._unrecognized = 0
        self._last_sequence: int | None = None
        self._last_timed_window: TimedWindow | None = None

    @property
    def state(self) -> ConnectionState:
        return self._connection.state

    def connect(self) -> None:
        self._connection.connect()

    def disconnect(self) -> None:
        self._connection.disconnect()

    def channels(self) -> Sequence[ChannelMetadata]:
        return self._channels

    def stats(self) -> LiveStats:
        return LiveStats(
            received_packets=self._received,
            dropped_packets=self._dropped,
            queue_depth=0,
            last_sequence_no=self._last_sequence,
        )

    @property
    def diagnostics(self) -> tuple[int, int]:
        """`(kesik_sayaci, taninmayan_sayaci)` — §2.1 tanılama olayları."""
        return (self._truncated, self._unrecognized)

    @property
    def last_timed_window(self) -> TimedWindow | None:
        """En son çözülen paketin `device_ticks`'ten hesaplanan kanonik penceresi.

        Yalnız `time_base` verilmişse dolar (`F5-013`); verilmemişse `None`.
        """
        return self._last_timed_window

    def packets(self) -> Iterator[LivePacket]:
        buffer = bytearray()
        for chunk in self._connection.read_chunks():
            buffer += chunk
            yield from self._drain(buffer)

    def _drain(self, buffer: bytearray) -> Iterator[LivePacket]:
        """Tamponda biriken kadar **tam** çerçeveyi sırayla çözer."""
        while True:
            try:
                total = peek_frame_length(bytes(buffer))
            except UnrecognizedFrameError:
                # Akis tekildir; UDP'nin aksine "bir sonraki datagram"a
                # gecilemez. Senkron kaybedildi, baglanti kapatilir.
                self._unrecognized += 1
                self._connection.disconnect()
                return
            if total is None or len(buffer) < total:
                return  # daha bayt bekleniyor

            try:
                header, payload = unpack_frame(bytes(buffer[:total]))
            except TruncatedDatagramError:  # pragma: no cover - peek zaten garanti eder
                self._truncated += 1
                del buffer[:total]
                continue
            del buffer[:total]

            try:
                chunks, events = decode_payload(payload)
            except TruncatedDatagramError:
                self._truncated += 1
                self._dropped += 1
                continue

            if self._time_base is not None:
                self._last_timed_window = timed_window_from_packet(
                    header, chunks, self._time_base, self._ticks0
                )

            self._received += 1
            self._last_sequence = header.sequence_no
            yield LivePacket(
                sequence_no=header.sequence_no,
                received_ns=self._clock_ns(),
                chunks=chunks,
                events=events,
            )
