"""TCP → domain akışı, uçtan uca — `F5-008`.

Kabul: bölünmüş veya aynı okumada gelen paketler tam bir kez çözülür.

Gerçek `socket.SOCK_STREAM` loopback üzerinden çalışır; hiçbir soket
mock'lanmaz. "Bölünmüş paket" senaryosu, iki yarı arasına gerçek bir
gecikme koyarak istemcinin bunları **gerçekten ayrı** `recv()` çağrılarıyla
almasını sağlar — tesadüfen birleşmelerine güvenilmez.
"""

from __future__ import annotations

import socket
import time
from collections.abc import Iterator

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.io.live.payload_codec import encode_payload
from sonar_analyzer.io.live.protocol import ConnectionState, LiveSource
from sonar_analyzer.io.live.tcp_connection import TcpConnection
from sonar_analyzer.io.live.tcp_live_source import TcpLiveSource
from sonar_analyzer.io.live.wire_header import PROTOCOL_TCP, LiveWireHeader, pack_frame


class _LocalServer:
    def __init__(self) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = int(self.listener.getsockname()[1])
        self.listener.settimeout(2.0)

    def accept(self) -> socket.socket:
        conn, _address = self.listener.accept()
        return conn

    def close(self) -> None:
        self.listener.close()


def _chunk(channel_id: str, n: int) -> DataChunk:
    timestamps = np.arange(n, dtype=np.int64) * 1_000_000
    values = np.linspace(0.0, 1.0, n, dtype=np.float64)
    return DataChunk(channel_id, timestamps, values)


def _frame(sequence_no: int, payload: bytes) -> bytes:
    header = LiveWireHeader(
        PROTOCOL_TCP,
        flags=0,
        sequence_no=sequence_no,
        fragment_index=0,
        fragment_count=1,
        device_ticks=0,
        payload_length=0,
    )
    return pack_frame(header, payload)


@pytest.fixture()
def server() -> Iterator[_LocalServer]:
    instance = _LocalServer()
    yield instance
    instance.close()


@pytest.fixture()
def source(server: _LocalServer) -> Iterator[tuple[TcpLiveSource, socket.socket]]:
    connection = TcpConnection("127.0.0.1", server.port, timeout_s=0.2)
    live = TcpLiveSource(connection)
    live.connect()
    accepted = server.accept()
    yield live, accepted
    live.disconnect()
    accepted.close()


# --------------------------------------------------------------------------- #
# tek okumada gelen tek cerceve
# --------------------------------------------------------------------------- #


def test_a_frame_delivered_in_a_single_read_decodes(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    live, accepted = source
    accepted.sendall(_frame(1, encode_payload([_chunk("ch0", 10)], [])))

    packet = next(iter(live.packets()))
    assert packet.sequence_no == 1
    assert packet.chunks[0].channel_id == "ch0"
    assert len(packet.chunks[0]) == 10


# --------------------------------------------------------------------------- #
# bolunmus paket
# --------------------------------------------------------------------------- #


def test_a_frame_split_across_two_real_reads_still_decodes_exactly_once(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    live, accepted = source
    frame = _frame(2, encode_payload([_chunk("ch0", 500)], []))
    midpoint = len(frame) // 2

    accepted.sendall(frame[:midpoint])
    time.sleep(0.05)  # istemcinin ilk yariyi AYRI bir recv() ile almasini garanti eder
    accepted.sendall(frame[midpoint:])

    packet = next(iter(live.packets()))
    assert packet.sequence_no == 2
    assert len(packet.chunks[0]) == 500


def test_a_frame_split_into_many_small_reads_still_decodes_exactly_once(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    live, accepted = source
    frame = _frame(3, encode_payload([_chunk("ch0", 50)], []))
    for start in range(0, len(frame), 7):  # 7 baytlik kucuk parcalar halinde gonder
        accepted.sendall(frame[start : start + 7])
        time.sleep(0.002)

    packet = next(iter(live.packets()))
    assert packet.sequence_no == 3
    assert len(packet.chunks[0]) == 50


# --------------------------------------------------------------------------- #
# ayni okumada birlesik paketler
# --------------------------------------------------------------------------- #


def test_two_frames_arriving_in_the_same_read_both_decode_exactly_once(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    live, accepted = source
    first = _frame(10, encode_payload([_chunk("ch0", 3)], []))
    second = _frame(11, encode_payload([_chunk("ch1", 4)], []))
    accepted.sendall(first + second)  # tek sendall -> yuksek olasilikla tek recv()

    iterator = live.packets()
    packet_a = next(iterator)
    packet_b = next(iterator)
    assert (packet_a.sequence_no, packet_b.sequence_no) == (10, 11)
    assert packet_a.chunks[0].channel_id == "ch0"
    assert packet_b.chunks[0].channel_id == "ch1"
    assert live.stats().received_packets == 2


def test_three_frames_merged_with_a_trailing_partial_fourth(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    """Aynı okumada üç tam çerçeve + dördüncünün başı — dördüncü sonra tamamlanır."""
    live, accepted = source
    frames = [_frame(i, encode_payload([_chunk(f"ch{i}", 5)], [])) for i in range(4)]
    merged_and_partial = b"".join(frames[:3]) + frames[3][:10]
    accepted.sendall(merged_and_partial)
    time.sleep(0.05)
    accepted.sendall(frames[3][10:])

    iterator = live.packets()
    received = [next(iterator) for _ in range(4)]
    assert [p.sequence_no for p in received] == [0, 1, 2, 3]
    assert live.stats().received_packets == 4


# --------------------------------------------------------------------------- #
# tanilama ve sozlesme
# --------------------------------------------------------------------------- #


def test_an_unrecognized_frame_is_diagnosed_and_the_connection_closes(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    """UDP'nin aksine akış tekildir — senkron kaybı bağlantıyı kapatır."""
    live, accepted = source
    accepted.sendall(b"XXXX" + b"0" * 30)  # gecersiz magic, en az 28 bayt

    with pytest.raises(StopIteration):
        next(iter(live.packets()))
    assert live.diagnostics == (0, 1)
    assert live.state is ConnectionState.DISCONNECTED


def test_satisfies_the_live_source_protocol(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    live, _accepted = source
    assert isinstance(live, LiveSource)


def test_disconnect_ends_the_packets_generator(
    source: tuple[TcpLiveSource, socket.socket],
) -> None:
    live, _accepted = source
    iterator = live.packets()
    live.disconnect()
    with pytest.raises(StopIteration):
        next(iterator)
