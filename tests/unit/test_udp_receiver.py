"""UDP alıcı bağlantısı — `F5-005`.

Kabul: yerel simülatör paketleri alınır; disconnect soketi serbest bırakır.

Testler gerçek `socket.SOCK_DGRAM` loopback (`127.0.0.1`) üzerinden çalışır;
hiçbir soket mock'lanmaz — "yerel simülatör paketleri alınır" iddiası
gerçek bir gönderici soketten gerçek baytlarla kanıtlanır.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator

import pytest

from sonar_analyzer.io.live.protocol import ConnectionState
from sonar_analyzer.io.live.udp_receiver import MAX_UDP_DATAGRAM_BYTES, UdpDatagramReceiver


def _send_from_a_local_simulator(port: int, payload: bytes) -> None:
    """Gerçek donanım yerine geçen, tek seferlik bir UDP göndericisi."""
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sender.sendto(payload, ("127.0.0.1", port))
    finally:
        sender.close()


@pytest.fixture()
def receiver() -> Iterator[UdpDatagramReceiver]:
    instance = UdpDatagramReceiver(port=0, timeout_s=0.2)
    yield instance
    instance.disconnect()  # test sirasinda birakilan soketleri temizle


# --------------------------------------------------------------------------- #
# baglanti yasam dongusu
# --------------------------------------------------------------------------- #


def test_starts_disconnected_and_connect_reaches_connected(receiver: UdpDatagramReceiver) -> None:
    assert receiver.state is ConnectionState.DISCONNECTED
    receiver.connect()
    assert receiver.state is ConnectionState.CONNECTED


def test_connect_binds_to_an_os_assigned_port_when_zero(receiver: UdpDatagramReceiver) -> None:
    receiver.connect()
    assert receiver.local_port > 0


def test_connect_is_idempotent_and_keeps_the_same_port(receiver: UdpDatagramReceiver) -> None:
    receiver.connect()
    port = receiver.local_port
    receiver.connect()
    assert receiver.local_port == port
    assert receiver.state is ConnectionState.CONNECTED


def test_local_port_before_connect_is_refused(receiver: UdpDatagramReceiver) -> None:
    with pytest.raises(RuntimeError, match="connect"):
        _ = receiver.local_port


def test_disconnect_before_connect_is_a_no_op(receiver: UdpDatagramReceiver) -> None:
    receiver.disconnect()
    assert receiver.state is ConnectionState.DISCONNECTED


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="timeout_s pozitif olmali"):
        UdpDatagramReceiver(timeout_s=0.0)


# --------------------------------------------------------------------------- #
# yerel simulator paketleri alinir
# --------------------------------------------------------------------------- #


def test_receives_a_datagram_from_a_local_simulator(receiver: UdpDatagramReceiver) -> None:
    receiver.connect()
    _send_from_a_local_simulator(receiver.local_port, b"merhaba sonar")

    payload = next(iter(receiver.datagrams()))
    assert payload == b"merhaba sonar"
    assert receiver.received_count == 1


def test_multiple_datagrams_arrive_in_order(receiver: UdpDatagramReceiver) -> None:
    receiver.connect()
    for index in range(5):
        _send_from_a_local_simulator(receiver.local_port, f"paket-{index}".encode("ascii"))

    iterator = receiver.datagrams()
    received = [next(iterator) for _ in range(5)]
    assert received == [f"paket-{index}".encode("ascii") for index in range(5)]
    assert receiver.received_count == 5


def test_a_datagram_at_the_wire_contract_safe_size_is_not_truncated(
    receiver: UdpDatagramReceiver,
) -> None:
    """`docs/live/protocol-contract.md` §3.1: güvenli tek-datagram sınırı 1444 bayt."""
    receiver.connect()
    payload = bytes(range(256)) * 5 + bytes(range(164))  # tam 1444 bayt, tanimlanabilir icerik
    assert len(payload) == 1444
    _send_from_a_local_simulator(receiver.local_port, payload)

    received = next(iter(receiver.datagrams()))
    assert received == payload
    assert len(received) == 1444


def test_receive_buffer_covers_the_maximum_udp_datagram(receiver: UdpDatagramReceiver) -> None:
    receiver.connect()
    payload = b"\xab" * MAX_UDP_DATAGRAM_BYTES
    _send_from_a_local_simulator(receiver.local_port, payload)

    received = next(iter(receiver.datagrams()))
    assert received == payload


# --------------------------------------------------------------------------- #
# disconnect soketi serbest birakir
# --------------------------------------------------------------------------- #


def test_disconnect_releases_the_port_for_immediate_reuse(receiver: UdpDatagramReceiver) -> None:
    """En sıkı kanıt: soket gerçekten kapanmadıysa aynı porta ikinci `bind()` başarısız olur."""
    receiver.connect()
    port = receiver.local_port
    receiver.disconnect()
    assert receiver.state is ConnectionState.DISCONNECTED

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.bind(("127.0.0.1", port))  # ilk soket kapanmadiysa OSError firlatir
    finally:
        probe.close()


def test_datagrams_iterator_ends_immediately_after_disconnect(
    receiver: UdpDatagramReceiver,
) -> None:
    receiver.connect()
    receiver.disconnect()
    assert list(receiver.datagrams()) == []


def test_disconnect_is_idempotent(receiver: UdpDatagramReceiver) -> None:
    receiver.connect()
    receiver.disconnect()
    receiver.disconnect()
    assert receiver.state is ConnectionState.DISCONNECTED


def test_disconnect_from_another_thread_interrupts_a_blocked_receive(
    receiver: UdpDatagramReceiver,
) -> None:
    """`recvfrom()` içinde bloke olmuşken bile `disconnect()` üretecı hemen bitirir."""
    receiver.connect()
    timer = threading.Timer(0.05, receiver.disconnect)
    timer.start()
    try:
        started = time.perf_counter()
        received = list(receiver.datagrams())  # hicbir sey gonderilmedi
        elapsed = time.perf_counter() - started
    finally:
        timer.cancel()

    assert received == []
    # 0.2 s'lik recv timeout'unu beklemeden, ~0.05 s'de kesilmeli.
    assert elapsed < 0.15
