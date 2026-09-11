"""Serial çerçeve sınırı ve zaman aşımı — `F5-010`.

`SerialConnection`'ın (`F5-009`) ham bayt akışını `docs/live/protocol-
contract.md` §3.3'ün çerçevesiyle birleştirir:

```
SYNC(2B, 0xAA 0x55) | LiveWireHeader(28B) | payload(N B) | crc32(4B LE)
```

Serial kendi bütünlük denetimi olmayan bir bayt akışıdır (gürültü, taşma,
yanlış baud ile bayt bozulabilir) — bu yüzden UDP/TCP'den iki farkı var:

1. **CRC her çerçevede zorunlu.** `crc32`, `LiveWireHeader + payload`
   üzerinden hesaplanır (Profil B'nin `RECORD_TRAILER` deseniyle aynı
   fikir). Uyuşmazsa çerçeve **tümüyle** atılır.
2. **Yeniden eşitleme (`resync`) vardır.** TCP'nin aksine (tek akış,
   senkron kaybı bağlantıyı kapatır) burada bozuk bir çerçeve sonraki
   çerçeveleri kilitlemez — alıcı sıradaki `SYNC` desenini arayarak
   yeniden eşitlenir.

Son geçerli (SYNC + geçerli CRC) çerçeveden sonra **1000 ms** içinde yeni
bir çerçeve görülmezse bağlantı `RECONNECTING`'e düşer
(`SerialConnection.report_silence_timeout`) — "sanal portta eksik paket
beklenir veya sözleşmeye göre raporlanır" kabul kriterinin ikinci yarısı.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.time_base import TimeBase
from sonar_analyzer.io.decoders.crc import crc32
from sonar_analyzer.io.live.live_time import TimedWindow, timed_window_from_packet
from sonar_analyzer.io.live.payload_codec import decode_payload
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.io.live.serial_connection import SerialConnection
from sonar_analyzer.io.live.wire_header import (
    TruncatedDatagramError,
    UnrecognizedFrameError,
    peek_frame_length,
    unpack_frame,
)

SYNC = b"\xaa\x55"
SYNC_SIZE = len(SYNC)
CRC_SIZE = 4
#: `docs/live/protocol-contract.md` §3.3.
SILENCE_TIMEOUT_NS = 1_000_000_000


class SerialLiveSource:
    """`LiveSource` sözleşmesini Serial tel protokolü üzerinden karşılar."""

    def __init__(
        self,
        connection: SerialConnection,
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
        self._buffer = bytearray()
        self._last_valid_ns = 0
        self._received = 0
        self._dropped = 0
        self._crc_errors = 0
        self._unrecognized = 0
        self._timeout_count = 0
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
    def diagnostics(self) -> tuple[int, int, int]:
        """`(crc_hatasi, taninmayan_sync, zaman_asimi)` — §3.3 tanılama sayaçları."""
        return (self._crc_errors, self._unrecognized, self._timeout_count)

    @property
    def last_timed_window(self) -> TimedWindow | None:
        """En son çözülen paketin `device_ticks`'ten hesaplanan kanonik penceresi.

        Yalnız `time_base` verilmişse dolar (`F5-013`); verilmemişse `None`.
        """
        return self._last_timed_window

    def packets(self) -> Iterator[LivePacket]:
        self._buffer = bytearray()
        self._last_valid_ns = self._clock_ns()
        for chunk in self._connection.read_chunks():
            if chunk:
                self._buffer += chunk
            yield from self._drain()
            if self._clock_ns() - self._last_valid_ns > SILENCE_TIMEOUT_NS:
                self._timeout_count += 1
                self._connection.report_silence_timeout()
                return

    def _drain(self) -> Iterator[LivePacket]:
        """Tamponda biriken kadar geçerli çerçeveyi çözer; bozuğu atlayıp yeniden eşitlenir."""
        while True:
            sync_at = self._buffer.find(SYNC)
            if sync_at == -1:
                # SYNC yok: son bayt bir sonraki SYNC'in ilk baytı olabilir, onu sakla.
                if len(self._buffer) > 1:
                    del self._buffer[: len(self._buffer) - 1]
                return
            if sync_at > 0:
                del self._buffer[:sync_at]  # SYNC'ten onceki copu at

            try:
                header_and_payload_len = peek_frame_length(bytes(self._buffer[SYNC_SIZE:]))
            except UnrecognizedFrameError:
                self._unrecognized += 1
                del self._buffer[:SYNC_SIZE]  # bu SYNC yanlis pozitifti; gec, yeniden ara
                continue
            if header_and_payload_len is None:
                return  # baslik icin daha bayt bekleniyor

            total = SYNC_SIZE + header_and_payload_len + CRC_SIZE
            if len(self._buffer) < total:
                return  # tam cerceve icin daha bayt bekleniyor

            body = bytes(self._buffer[SYNC_SIZE : SYNC_SIZE + header_and_payload_len])
            stored_crc = int.from_bytes(
                self._buffer[SYNC_SIZE + header_and_payload_len : total], "little"
            )
            if crc32(body) != stored_crc:
                self._crc_errors += 1
                self._dropped += 1
                del self._buffer[:total]  # cerceve tumuyle atilir
                continue

            del self._buffer[:total]
            try:
                header, payload = unpack_frame(body)
                chunks, events = decode_payload(payload)
            except TruncatedDatagramError:  # pragma: no cover - CRC zaten butunlugu dogruladi
                self._dropped += 1
                continue

            if self._time_base is not None:
                self._last_timed_window = timed_window_from_packet(
                    header, chunks, self._time_base, self._ticks0
                )

            self._last_valid_ns = self._clock_ns()
            self._received += 1
            self._last_sequence = header.sequence_no
            yield LivePacket(
                sequence_no=header.sequence_no,
                received_ns=self._clock_ns(),
                chunks=chunks,
                events=events,
            )
