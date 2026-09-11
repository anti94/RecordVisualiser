"""Üç adaptör (+ replay) için ortak `LiveSource` sözleşme kontrolü — `F5-011`.

Kabul: connect, packets ve disconnect davranışı yerel/sanal kaynakla eşleşir.

`F5-003`–`F5-010` dört ayrı `LiveSource` gerçeklemesi kurdu
(`FileReplaySource`, `UdpLiveSource`, `TcpLiveSource`, `SerialLiveSource`);
her birinin kendi dosyasında ayrıntılı testi var. Bu dosya farklı bir
soruyu sorar: dördü de **aynı** temel sözleşmeye mi uyuyor? Aynı senaryo
dizisi (bağlanmadan önce boş akış, `connect`/`disconnect` idempotentliği,
gerçek bir paketin ulaşması, `disconnect` sonrası akışın kesilmesi) dördüne
de **aynı assertion'larla** uygulanır — hiçbiri diğerinden farklı
davranmaz.
"""

from __future__ import annotations

import socket
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.io.decoders.crc import crc32
from sonar_analyzer.io.live.file_replay_source import FileReplaySource
from sonar_analyzer.io.live.payload_codec import encode_payload
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveSource
from sonar_analyzer.io.live.serial_connection import SerialConnection, SerialPortConfig
from sonar_analyzer.io.live.serial_live_source import SYNC, SerialLiveSource
from sonar_analyzer.io.live.tcp_connection import TcpConnection
from sonar_analyzer.io.live.tcp_live_source import TcpLiveSource
from sonar_analyzer.io.live.udp_live_source import UdpLiveSource
from sonar_analyzer.io.live.udp_receiver import UdpDatagramReceiver
from sonar_analyzer.io.live.wire_header import (
    PROTOCOL_SERIAL,
    PROTOCOL_TCP,
    PROTOCOL_UDP,
    LiveWireHeader,
    pack_frame,
)
from sonar_analyzer.repository.mock_repository import MockRecordingRepository


def _chunk(channel_id: str = "ch0", n: int = 3) -> DataChunk:
    timestamps = np.arange(n, dtype=np.int64) * 1_000_000
    values = np.linspace(0.0, 1.0, n, dtype=np.float64)
    return DataChunk(channel_id, timestamps, values)


@dataclass
class _Scenario:
    """Bir `LiveSource` gerçeklemesini ortak testin sürebileceği biçime sarar."""

    name: str
    source: LiveSource
    #: `connect()`den sonra çağrılır; en az bir paketlik veri kaynağa ulaştırır.
    arrange_one_packet: Callable[[], None]
    #: Test sonunda dış kaynakları (soket, sunucu) bırakır.
    cleanup: Callable[[], None] = field(default=lambda: None)


# --------------------------------------------------------------------------- #
# dosya replay
# --------------------------------------------------------------------------- #


def _file_replay_scenario() -> _Scenario:
    repository = MockRecordingRepository(duration_s=1.0)
    source = FileReplaySource(repository, sleep=lambda _seconds: None)
    return _Scenario("file-replay", source, arrange_one_packet=lambda: None)


# --------------------------------------------------------------------------- #
# udp
# --------------------------------------------------------------------------- #


def _udp_scenario() -> _Scenario:
    receiver = UdpDatagramReceiver(port=0, timeout_s=0.1)
    source = UdpLiveSource(receiver)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def arrange_one_packet() -> None:
        header = LiveWireHeader(
            PROTOCOL_UDP,
            flags=0,
            sequence_no=0,
            fragment_index=0,
            fragment_count=1,
            device_ticks=0,
            payload_length=0,
        )
        frame = pack_frame(header, encode_payload([_chunk()], []))
        sender.sendto(frame, ("127.0.0.1", receiver.local_port))

    return _Scenario("udp", source, arrange_one_packet, cleanup=sender.close)


# --------------------------------------------------------------------------- #
# tcp
# --------------------------------------------------------------------------- #


def _tcp_scenario() -> _Scenario:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    # Backlog > 1: reconnect testi accept() cagirmadan ikinci kez baglanir;
    # dar bir backlog, kabul edilmemis ilk baglantiyi kuyrukta tutup ikinci
    # connect()'i gercekten zaman asimina ugratir (bulundu, elle dogrulandi).
    listener.listen(5)
    listener.settimeout(2.0)
    port = int(listener.getsockname()[1])
    connection = TcpConnection("127.0.0.1", port, timeout_s=0.2)
    source = TcpLiveSource(connection)
    accepted_holder: list[socket.socket] = []

    def arrange_one_packet() -> None:
        accepted = listener.accept()[0]
        accepted_holder.append(accepted)
        header = LiveWireHeader(
            PROTOCOL_TCP,
            flags=0,
            sequence_no=0,
            fragment_index=0,
            fragment_count=1,
            device_ticks=0,
            payload_length=0,
        )
        accepted.sendall(pack_frame(header, encode_payload([_chunk()], [])))

    def cleanup() -> None:
        for accepted in accepted_holder:
            accepted.close()
        listener.close()

    return _Scenario("tcp", source, arrange_one_packet, cleanup)


# --------------------------------------------------------------------------- #
# serial (sahte aktarim - donanim yok)
# --------------------------------------------------------------------------- #


class _FakeClock:
    def __init__(self) -> None:
        self.now_ns = 0

    def __call__(self) -> int:
        return self.now_ns


class _ScriptedSerialTransport:
    def __init__(self) -> None:
        self._script: list[bytes] = []
        self.closed = False

    def push(self, data: bytes) -> None:
        self._script.append(data)

    def read(self, size: int = 1) -> bytes:
        return self._script.pop(0) if self._script else b""

    def write(self, data: bytes) -> int | None:
        return len(data)

    def close(self) -> None:
        self.closed = True


def _serial_scenario() -> _Scenario:
    transport = _ScriptedSerialTransport()
    config = SerialPortConfig(port="COM9", baud_rate=115200)
    connection = SerialConnection(
        config, timeout_s=0.05, transport_factory=lambda _cfg, _t: transport
    )
    source = SerialLiveSource(connection, clock_ns=_FakeClock())

    def arrange_one_packet() -> None:
        header = LiveWireHeader(
            PROTOCOL_SERIAL,
            flags=0,
            sequence_no=0,
            fragment_index=0,
            fragment_count=1,
            device_ticks=0,
            payload_length=0,
        )
        body = pack_frame(header, encode_payload([_chunk()], []))
        transport.push(SYNC + body + crc32(body).to_bytes(4, "little"))

    return _Scenario("serial", source, arrange_one_packet)


_SCENARIO_BUILDERS: tuple[Callable[[], _Scenario], ...] = (
    _file_replay_scenario,
    _udp_scenario,
    _tcp_scenario,
    _serial_scenario,
)


@pytest.fixture(params=_SCENARIO_BUILDERS, ids=[b.__name__ for b in _SCENARIO_BUILDERS])
def scenario(request: pytest.FixtureRequest) -> Iterator[_Scenario]:
    built = request.param()
    try:
        yield built
    finally:
        built.cleanup()


# --------------------------------------------------------------------------- #
# ortak sozlesme
# --------------------------------------------------------------------------- #


def test_every_adapter_satisfies_the_live_source_protocol(scenario: _Scenario) -> None:
    assert isinstance(scenario.source, LiveSource)


def test_every_adapter_starts_disconnected(scenario: _Scenario) -> None:
    assert scenario.source.state is ConnectionState.DISCONNECTED


def test_every_adapter_yields_nothing_before_connect(scenario: _Scenario) -> None:
    assert list(scenario.source.packets()) == []


def test_every_adapter_reaches_connected_and_connect_is_idempotent(scenario: _Scenario) -> None:
    source = scenario.source
    source.connect()
    assert source.state is ConnectionState.CONNECTED
    source.connect()  # ikinci cagri hata vermemeli, durumu degistirmemeli
    assert source.state is ConnectionState.CONNECTED


def test_every_adapter_delivers_a_real_packet_after_connect(scenario: _Scenario) -> None:
    source = scenario.source
    source.connect()
    scenario.arrange_one_packet()

    packet = next(iter(source.packets()))
    assert isinstance(packet, LivePacket)
    assert packet.sequence_no >= 0
    assert source.stats().received_packets >= 1


def test_every_adapter_channels_call_does_not_raise(scenario: _Scenario) -> None:
    source = scenario.source
    source.connect()
    assert list(source.channels()) == list(source.channels())  # en azindan kararli/yinelenebilir


def test_every_adapter_disconnect_ends_an_in_flight_iterator(scenario: _Scenario) -> None:
    source = scenario.source
    source.connect()
    iterator = source.packets()
    source.disconnect()
    assert source.state is ConnectionState.DISCONNECTED
    with pytest.raises(StopIteration):
        next(iterator)


def test_every_adapter_disconnect_is_idempotent(scenario: _Scenario) -> None:
    source = scenario.source
    source.connect()
    source.disconnect()
    source.disconnect()  # ikinci cagri hata vermemeli
    assert source.state is ConnectionState.DISCONNECTED


def test_every_adapter_can_reconnect_after_disconnect(scenario: _Scenario) -> None:
    """Bağlan → kopar → tekrar bağlan: dördü de aynı döngüyü destekler."""
    source = scenario.source
    source.connect()
    source.disconnect()
    source.connect()
    assert source.state is ConnectionState.CONNECTED


def test_every_adapter_state_is_the_shared_connection_state_type(scenario: _Scenario) -> None:
    """Dört adaptör da `F5-002`'nin `ConnectionState`'ini paylaşır — kendi tipini icat etmez."""
    source = scenario.source
    assert isinstance(source.state, ConnectionState)
    source.connect()
    assert isinstance(source.state, ConnectionState)
