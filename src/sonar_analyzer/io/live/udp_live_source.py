"""UDP tabanlı tam `LiveSource` — `F5-006`.

`UdpDatagramReceiver` (`F5-005`, ham bayt) ile `wire_header`/`payload_codec`
(`LiveWireHeader` çözümü ve kanal/olay kodlaması) burada birleşir:
`docs/live/protocol-contract.md` §3.1'in **parçalama ve kayıp politikasını**
uygulayan tek yer.

Geçerli bir datagram domain verisine (`LivePacket`) dönüşür; kesik veya
tanınmayan bir datagram **teşhis edilir** (`TruncatedDatagramError`/
`UnrecognizedFrameError` sayaçları — `diagnostics` özelliği) ve sessizce
yutulmaz, ama akışı da durdurmaz — sözleşmenin "ya tam pencere ya hiç"
ilkesiyle o tek pencere kayıp sayılır, sonraki pencereler etkilenmez.

**Bilinen sınır:** `resolved` kümesi bir oturum boyunca sınırsız büyür
(eski `sequence_no`'lar hiç budanmaz). Kuyruk/bellek sınırlaması genel
olarak `F5-012`–`F5-016`'nın işidir; burada yalnız tel çözümü doğru
çalışır, uzun ömürlü bellek bütçesi bu işin kapsamı dışıdır.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.time_base import TimeBase
from sonar_analyzer.io.live.live_time import TimedWindow, timed_window_from_packet
from sonar_analyzer.io.live.payload_codec import decode_payload
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.io.live.udp_receiver import UdpDatagramReceiver
from sonar_analyzer.io.live.wire_header import (
    PROTOCOL_UDP,
    TruncatedDatagramError,
    UnrecognizedFrameError,
    unpack_frame,
)

#: `docs/live/protocol-contract.md` §3.1 — pencere süresinin 4 katı.
REASSEMBLY_TIMEOUT_NS = 500_000_000


class UdpLiveSource:
    """`LiveSource` sözleşmesini UDP tel protokolü üzerinden karşılar."""

    def __init__(
        self,
        receiver: UdpDatagramReceiver | None = None,
        *,
        channels: Sequence[ChannelMetadata] = (),
        clock_ns: Callable[[], int] = time.time_ns,
        time_base: TimeBase | None = None,
        ticks0: int = 0,
    ) -> None:
        self._receiver = receiver if receiver is not None else UdpDatagramReceiver()
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
        return self._receiver.state

    @property
    def local_port(self) -> int:
        """Gerçekten bağlanılan yerel UDP portu (tanılama/log için)."""
        return self._receiver.local_port

    def connect(self) -> None:
        self._receiver.connect()

    def disconnect(self) -> None:
        self._receiver.disconnect()

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
        """`(kesik_sayaci, taninmayan_sayaci)` — §2.1/§3.1 tanılama olayları."""
        return (self._truncated, self._unrecognized)

    @property
    def last_timed_window(self) -> TimedWindow | None:
        """En son çözülen paketin `device_ticks`'ten hesaplanan kanonik penceresi.

        Yalnız `time_base` verilmişse dolar (`F5-013`); verilmemişse `None`.
        """
        return self._last_timed_window

    def packets(self) -> Iterator[LivePacket]:
        pending: dict[int, dict[int, bytes]] = {}
        expected_fragments: dict[int, int] = {}
        deadlines: dict[int, int] = {}
        resolved: set[int] = set()

        for datagram in self._receiver.datagrams():
            now = self._clock_ns()
            for seq in [s for s, deadline in deadlines.items() if now > deadline]:
                del pending[seq]
                del expected_fragments[seq]
                del deadlines[seq]
                resolved.add(seq)
                self._dropped += 1

            try:
                header, fragment_payload = unpack_frame(datagram)
            except TruncatedDatagramError:
                self._truncated += 1
                continue
            except UnrecognizedFrameError:
                self._unrecognized += 1
                continue

            if header.protocol_id != PROTOCOL_UDP:
                self._unrecognized += 1
                continue

            seq = header.sequence_no
            if seq in resolved:
                continue  # cozulmus/zaman asimina ugramis pencereye gec gelen parca

            fragments = pending.setdefault(seq, {})
            fragments[header.fragment_index] = fragment_payload
            expected_fragments[seq] = header.fragment_count
            deadlines.setdefault(seq, now + REASSEMBLY_TIMEOUT_NS)

            if len(fragments) < expected_fragments[seq]:
                continue  # daha parca bekleniyor

            full_payload = b"".join(fragments[index] for index in range(expected_fragments[seq]))
            del pending[seq]
            del expected_fragments[seq]
            del deadlines[seq]
            resolved.add(seq)

            try:
                chunks, events = decode_payload(full_payload)
            except TruncatedDatagramError:
                self._truncated += 1
                self._dropped += 1
                continue

            if self._time_base is not None:
                self._last_timed_window = timed_window_from_packet(
                    header, chunks, self._time_base, self._ticks0
                )

            self._received += 1
            self._last_sequence = seq
            yield LivePacket(sequence_no=seq, received_ns=now, chunks=chunks, events=events)
