"""UDP → domain akışı, uçtan uca — `F5-006`.

Kabul: geçerli datagram domain verisi olur; kesik datagram teşhis edilir.

Gerçek `socket.SOCK_DGRAM` loopback üzerinden çalışır; hiçbir soket
mock'lanmaz. Zaman aşımı senaryoları için `clock_ns` enjekte edilir —
gerçek 500 ms beklemeden test edilir.
"""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterator

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.payload_codec import encode_payload
from sonar_analyzer.io.live.protocol import ConnectionState, LiveSource
from sonar_analyzer.io.live.udp_live_source import UdpLiveSource
from sonar_analyzer.io.live.udp_receiver import UdpDatagramReceiver
from sonar_analyzer.io.live.wire_header import PROTOCOL_UDP, LiveWireHeader, pack_frame

DEVICE_TICKS = 1_788_901_200_000


class _FakeClock:
    """`clock_ns` yerine geçer — gerçek zaman aşımı beklemeden ilerletilir."""

    def __init__(self, start_ns: int = 0) -> None:
        self.now_ns = start_ns

    def __call__(self) -> int:
        return self.now_ns


def _chunk(channel_id: str, n: int) -> DataChunk:
    timestamps = np.arange(n, dtype=np.int64) * 1_000_000
    values = np.linspace(0.0, 1.0, n, dtype=np.float64)
    return DataChunk(channel_id, timestamps, values)


_EVENT = Event(
    timestamp_ns=0,
    source="live",
    category="sistem",
    severity=Severity.INFO,
    code="",
    message="baglanti testi",
)


def _send_frame(
    sock: socket.socket,
    port: int,
    *,
    sequence_no: int,
    payload: bytes,
    fragment_index: int = 0,
    fragment_count: int = 1,
    device_ticks: int = DEVICE_TICKS,
) -> None:
    header = LiveWireHeader(
        PROTOCOL_UDP,
        flags=0,
        sequence_no=sequence_no,
        fragment_index=fragment_index,
        fragment_count=fragment_count,
        device_ticks=device_ticks,
        payload_length=0,
    )
    sock.sendto(pack_frame(header, payload), ("127.0.0.1", port))


@pytest.fixture()
def sender() -> Iterator[socket.socket]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    yield sock
    sock.close()


@pytest.fixture()
def source() -> Iterator[UdpLiveSource]:
    instance = UdpLiveSource(UdpDatagramReceiver(port=0, timeout_s=0.2))
    instance.connect()
    yield instance
    instance.disconnect()


# --------------------------------------------------------------------------- #
# gecerli datagram domain verisi olur
# --------------------------------------------------------------------------- #


def test_a_single_fragment_datagram_becomes_a_live_packet(
    source: UdpLiveSource, sender: socket.socket
) -> None:
    port = source.local_port
    payload = encode_payload([_chunk("ch0", 50)], [_EVENT])
    _send_frame(sender, port, sequence_no=7, payload=payload)

    packet = next(iter(source.packets()))
    assert packet.sequence_no == 7
    assert len(packet.chunks) == 1
    assert packet.chunks[0].channel_id == "ch0"
    assert len(packet.events) == 1
    assert packet.events[0].code == _EVENT.code
    assert source.stats().received_packets == 1
    assert source.stats().last_sequence_no == 7


def test_fragments_reassemble_in_declared_index_order(
    source: UdpLiveSource, sender: socket.socket
) -> None:
    port = source.local_port
    payload = encode_payload([_chunk("acoustic0", 3000)], [])
    third = len(payload) // 3 + 1
    pieces = [payload[i : i + third] for i in range(0, len(payload), third)]
    assert len(pieces) == 3

    for index, piece in enumerate(pieces):
        _send_frame(
            sender,
            port,
            sequence_no=1,
            payload=piece,
            fragment_index=index,
            fragment_count=len(pieces),
        )

    packet = next(iter(source.packets()))
    assert packet.chunks[0].channel_id == "acoustic0"
    assert len(packet.chunks[0]) == 3000


def test_out_of_order_fragment_arrival_still_reassembles(
    source: UdpLiveSource, sender: socket.socket
) -> None:
    """Yeniden birleştirme `fragment_index`'e göredir, varış sırasına değil."""
    port = source.local_port
    payload = encode_payload([_chunk("ch0", 900)], [])
    third = len(payload) // 3 + 1
    pieces = [payload[i : i + third] for i in range(0, len(payload), third)]
    assert len(pieces) == 3

    for index in reversed(range(len(pieces))):  # tersten gonder
        _send_frame(
            sender,
            port,
            sequence_no=2,
            payload=pieces[index],
            fragment_index=index,
            fragment_count=len(pieces),
        )

    packet = next(iter(source.packets()))
    assert len(packet.chunks[0]) == 900
    assert packet.chunks[0].values.tolist() == _chunk("ch0", 900).values.tolist()


# --------------------------------------------------------------------------- #
# kesik / taninmayan datagram teshis edilir, akisi durdurmaz
# --------------------------------------------------------------------------- #


def test_incomplete_fragments_are_dropped_after_the_timeout(
    sender: socket.socket,
) -> None:
    """Zaman aşımı, yalnız **sonraki** bir datagram işlenirken kontrol edilir.

    Bu yüzden ikinci datagram, ilkinin işlenmesi (ve bekleme durumuna
    girmesi) **gerçekten bittikten sonra**, ayrı bir iş parçacığından
    saatı ilerletip gönderiliyor — ikisi birden önceden gönderilseydi
    işleme aynı `now` anında art arda olur, `now > deadline` hiç doğru
    olmazdı.
    """
    clock = _FakeClock(start_ns=0)
    receiver = UdpDatagramReceiver(port=0, timeout_s=0.05)
    source = UdpLiveSource(receiver, clock_ns=clock)
    source.connect()
    try:
        port = receiver.local_port
        payload = encode_payload([_chunk("ch0", 900)], [])
        third = len(payload) // 3 + 1
        pieces = [payload[i : i + third] for i in range(0, len(payload), third)]
        assert len(pieces) == 3

        _send_frame(
            sender, port, sequence_no=0, payload=pieces[0], fragment_index=0, fragment_count=3
        )  # yalnizca 1/3 parca

        def advance_clock_and_send_second() -> None:
            clock.now_ns = RECORD_PERIOD_NS * 5  # 500 ms zaman asimini kesinlikle asar
            _send_frame(sender, port, sequence_no=1, payload=encode_payload([_chunk("ch1", 5)], []))

        timer = threading.Timer(0.03, advance_clock_and_send_second)
        timer.start()
        try:
            packet = next(iter(source.packets()))
        finally:
            timer.cancel()

        assert packet.sequence_no == 1  # seq=0 hic yayinlanmadi
        assert source.stats().dropped_packets == 1
        assert source.stats().received_packets == 1
    finally:
        source.disconnect()


def test_a_garbage_datagram_with_the_wrong_magic_is_diagnosed_as_unrecognized(
    source: UdpLiveSource, sender: socket.socket
) -> None:
    """En az 28 bayt (başlık boyu) ama `magic` yanlış — "kesik" değil "tanınmayan"."""
    garbage = b"XXXX" + b"bu bir SNLV cercevesi degil, ama en az 28 bayt uzunlukta"
    assert len(garbage) >= 28
    sender.sendto(garbage, ("127.0.0.1", port := source.local_port))
    _send_frame(sender, port, sequence_no=5, payload=encode_payload([_chunk("ch0", 2)], []))

    packet = next(iter(source.packets()))
    assert packet.sequence_no == 5
    assert source.diagnostics == (0, 1)  # (kesik, taninmayan)


def test_a_datagram_shorter_than_the_header_is_diagnosed_as_truncated(
    source: UdpLiveSource, sender: socket.socket
) -> None:
    port = source.local_port
    sender.sendto(b"cok kisa", ("127.0.0.1", port))  # 28 bayttan kisa
    _send_frame(sender, port, sequence_no=6, payload=encode_payload([_chunk("ch0", 2)], []))

    packet = next(iter(source.packets()))
    assert packet.sequence_no == 6
    assert source.diagnostics == (1, 0)  # (kesik, taninmayan)


def test_a_frame_with_a_truncated_payload_is_diagnosed_and_does_not_stop_the_stream(
    source: UdpLiveSource, sender: socket.socket
) -> None:
    port = source.local_port
    header = LiveWireHeader(
        PROTOCOL_UDP,
        0,
        sequence_no=9,
        fragment_index=0,
        fragment_count=1,
        device_ticks=0,
        payload_length=0,
    )
    full_payload = encode_payload([_chunk("ch0", 100)], [])
    frame = pack_frame(header, full_payload)
    truncated_frame = frame[:-40]  # basligi koru, payload'i erken kes
    sender.sendto(truncated_frame, ("127.0.0.1", port))
    _send_frame(sender, port, sequence_no=10, payload=encode_payload([_chunk("ch0", 2)], []))

    packet = next(iter(source.packets()))
    assert packet.sequence_no == 10
    truncated_count, _unrecognized = source.diagnostics
    assert truncated_count >= 1


# --------------------------------------------------------------------------- #
# sozlesme
# --------------------------------------------------------------------------- #


def test_satisfies_the_live_source_protocol(source: UdpLiveSource) -> None:
    assert isinstance(source, LiveSource)


def test_disconnect_ends_the_packets_generator(
    source: UdpLiveSource,
) -> None:
    iterator = source.packets()
    source.disconnect()
    assert source.state is ConnectionState.DISCONNECTED
    with pytest.raises(StopIteration):
        next(iterator)
