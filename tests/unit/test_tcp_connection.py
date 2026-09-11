"""TCP bağlantı ve okuma akışı — `F5-007`.

Kabul: yerel sunucuya bağlanır; EOF ve bağlantı hatası doğru duruma geçer.

Testler gerçek `socket.SOCK_STREAM` loopback üzerinden çalışır — hiçbir
soket mock'lanmaz. "Bağlantı hatası", karşı ucu `SO_LINGER` ile sıfıra
ayarlayıp kapatarak (düzgün FIN yerine RST göndererek) **gerçekten**
üretiliyor; taklit edilmiyor.
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from collections.abc import Iterator

import pytest

from sonar_analyzer.io.live.protocol import ConnectionState
from sonar_analyzer.io.live.tcp_connection import TcpConnection


class _LocalServer:
    """Testteki "yerel sunucu" — gerçek bir dinleyici soket."""

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


def _reset(sock: socket.socket) -> None:
    """`FIN` yerine `RST` göndererek gerçek bir bağlantı hatası üretir."""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    sock.close()


@pytest.fixture()
def server() -> Iterator[_LocalServer]:
    instance = _LocalServer()
    yield instance
    instance.close()


@pytest.fixture()
def connection(server: _LocalServer) -> Iterator[TcpConnection]:
    instance = TcpConnection("127.0.0.1", server.port, timeout_s=0.1)
    yield instance
    instance.disconnect()


# --------------------------------------------------------------------------- #
# yerel sunucuya baglanir
# --------------------------------------------------------------------------- #


def test_connects_to_a_local_server(connection: TcpConnection, server: _LocalServer) -> None:
    assert connection.state is ConnectionState.DISCONNECTED
    connection.connect()
    server.accept()
    assert connection.state is ConnectionState.CONNECTED


def test_connect_is_idempotent(connection: TcpConnection, server: _LocalServer) -> None:
    connection.connect()
    server.accept()
    connection.connect()
    assert connection.state is ConnectionState.CONNECTED


def test_connecting_without_a_listening_server_raises_and_stays_disconnected() -> None:
    closed_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    closed_server.bind(("127.0.0.1", 0))
    port = closed_server.getsockname()[1]
    closed_server.close()  # kimse dinlemiyor

    connection = TcpConnection("127.0.0.1", port, timeout_s=0.2)
    with pytest.raises(OSError):
        connection.connect()
    assert connection.state is ConnectionState.DISCONNECTED


def test_disconnect_before_connect_is_a_no_op(connection: TcpConnection) -> None:
    connection.disconnect()
    assert connection.state is ConnectionState.DISCONNECTED


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="timeout_s pozitif olmali"):
        TcpConnection("127.0.0.1", 0, timeout_s=0.0)


# --------------------------------------------------------------------------- #
# okuma
# --------------------------------------------------------------------------- #


def test_receives_bytes_sent_by_the_server(connection: TcpConnection, server: _LocalServer) -> None:
    connection.connect()
    accepted = server.accept()
    accepted.sendall(b"merhaba istemci")

    received = next(iter(connection.read_chunks()))
    assert received == b"merhaba istemci"


def test_multiple_sends_are_received_as_the_same_concatenated_bytes(
    connection: TcpConnection, server: _LocalServer
) -> None:
    """TCP bir bayt akışıdır: parça sınırları korunmayabilir, toplam içerik korunur."""
    connection.connect()
    accepted = server.accept()
    accepted.sendall(b"birinci-")
    accepted.sendall(b"ikinci-")
    accepted.sendall(b"ucuncu")

    collected = bytearray()
    for chunk in connection.read_chunks():
        collected += chunk
        if collected == b"birinci-ikinci-ucuncu":
            break
    assert bytes(collected) == b"birinci-ikinci-ucuncu"


# --------------------------------------------------------------------------- #
# eof ve baglanti hatasi dogru duruma gecer
# --------------------------------------------------------------------------- #


def test_a_graceful_close_is_eof_and_transitions_to_disconnected(
    connection: TcpConnection, server: _LocalServer
) -> None:
    connection.connect()
    accepted = server.accept()
    accepted.sendall(b"son mesaj")
    accepted.shutdown(socket.SHUT_WR)  # duzgun FIN, RST degil

    chunks = list(connection.read_chunks())
    assert b"".join(chunks) == b"son mesaj"
    assert connection.state is ConnectionState.DISCONNECTED
    accepted.close()


def test_a_reset_connection_transitions_to_reconnecting_not_disconnected(
    connection: TcpConnection, server: _LocalServer
) -> None:
    """`RST`, "degraded"/toparlanma adayıdır — temiz kapanışla (`DISCONNECTED`) karıştırılmaz."""
    connection.connect()
    accepted = server.accept()
    _reset(accepted)

    with pytest.raises(StopIteration):
        next(iter(connection.read_chunks()))
    assert connection.state is ConnectionState.RECONNECTING


def test_eof_after_partial_data_still_yields_the_data_before_stopping(
    connection: TcpConnection, server: _LocalServer
) -> None:
    connection.connect()
    accepted = server.accept()
    accepted.sendall(b"veri")
    accepted.close()  # gonderici de kapatiyor -> EOF

    iterator = connection.read_chunks()
    first = next(iterator)
    assert first == b"veri"
    with pytest.raises(StopIteration):
        next(iterator)
    assert connection.state is ConnectionState.DISCONNECTED


# --------------------------------------------------------------------------- #
# disconnect
# --------------------------------------------------------------------------- #


def test_disconnect_stops_reading_immediately(
    connection: TcpConnection, server: _LocalServer
) -> None:
    connection.connect()
    server.accept()
    connection.disconnect()
    assert list(connection.read_chunks()) == []


def test_disconnect_is_idempotent(connection: TcpConnection, server: _LocalServer) -> None:
    connection.connect()
    server.accept()
    connection.disconnect()
    connection.disconnect()
    assert connection.state is ConnectionState.DISCONNECTED


def test_disconnect_from_another_thread_interrupts_a_blocked_read(
    connection: TcpConnection, server: _LocalServer
) -> None:
    connection.connect()
    server.accept()  # hicbir sey gondermiyor
    timer = threading.Timer(0.05, connection.disconnect)
    timer.start()
    try:
        started = time.perf_counter()
        received = list(connection.read_chunks())
        elapsed = time.perf_counter() - started
    finally:
        timer.cancel()

    assert received == []
    assert elapsed < 0.3  # 0.1 s'lik recv timeout'una takilsa bile makul ust sinir
