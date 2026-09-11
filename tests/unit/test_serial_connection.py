"""Serial port ayarı ve bağlantısı — `F5-009`.

Kabul: port ve hız doğrulanır; kapatma kaynağı serbest bırakır.

Gerçek seri port donanımı bu ortamda yok; bağlantı yaşam döngüsü
(`connect`/`disconnect`, kaynak serbest bırakma, idempotentlik) enjekte
edilen sahte bir aktarımla gerçek sınıf koduna karşı test edilir —
`FileReplaySource`'un `sleep`/`clock_ns` enjeksiyonuyla aynı ilke.
`pyserial` gerçekten kurulu değildir; öntanımlı üreticinin bunu açıkça
söylediği ayrıca **gerçek** (taklitsiz) bir testle doğrulanır.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.live.protocol import ConnectionState
from sonar_analyzer.io.live.serial_connection import (
    STANDARD_BAUD_RATES,
    SerialConnection,
    SerialPortConfig,
)


class _FakeTransport:
    def __init__(self) -> None:
        self.closed = False
        self.written: list[bytes] = []

    def read(self, size: int = 1) -> bytes:
        return b""

    def write(self, data: bytes) -> int | None:
        self.written.append(data)
        return len(data)

    def close(self) -> None:
        self.closed = True


class _FakeTransportFactory:
    """Enjekte edilen üretici: her `connect()`'te bir sahte aktarım döndürür."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[SerialPortConfig, float]] = []
        self.transports: list[_FakeTransport] = []

    def __call__(self, config: SerialPortConfig, timeout_s: float) -> _FakeTransport:
        self.calls.append((config, timeout_s))
        if self.fail:
            raise OSError(f"port acilamadi: {config.port}")
        transport = _FakeTransport()
        self.transports.append(transport)
        return transport


_CONFIG = SerialPortConfig(port="COM3", baud_rate=115200)


# --------------------------------------------------------------------------- #
# port ve hiz dogrulanir
# --------------------------------------------------------------------------- #


def test_a_valid_config_is_accepted() -> None:
    config = SerialPortConfig(port="COM3", baud_rate=115200)
    assert config.port == "COM3"
    assert config.baud_rate == 115200


def test_an_empty_port_is_refused() -> None:
    with pytest.raises(ValueError, match="Port adi bos olamaz"):
        SerialPortConfig(port="", baud_rate=9600)


def test_a_blank_port_is_refused() -> None:
    with pytest.raises(ValueError, match="Port adi bos olamaz"):
        SerialPortConfig(port="   ", baud_rate=9600)


@pytest.mark.parametrize("port", ["USB0", "3", "COM", "COMx", "ttyUSB0", "/dev/ttyUSB0"])
def test_a_non_windows_port_name_is_refused(port: str) -> None:
    """Bu ortam Windows'tur; `COMx` dışındaki adlar reddedilir."""
    with pytest.raises(ValueError, match="bicimini izlemeli"):
        SerialPortConfig(port=port, baud_rate=9600)


@pytest.mark.parametrize("port", ["COM1", "COM3", "COM22", "com5"])
def test_windows_port_names_of_any_digit_count_are_accepted(port: str) -> None:
    SerialPortConfig(port=port, baud_rate=9600)  # exception firlatmamali


@pytest.mark.parametrize("baud_rate", sorted(STANDARD_BAUD_RATES))
def test_every_standard_baud_rate_is_accepted(baud_rate: int) -> None:
    SerialPortConfig(port="COM1", baud_rate=baud_rate)


@pytest.mark.parametrize("baud_rate", [0, -9600, 12345, 100])
def test_a_non_standard_baud_rate_is_refused(baud_rate: int) -> None:
    with pytest.raises(ValueError, match="Desteklenmeyen baud hizi"):
        SerialPortConfig(port="COM1", baud_rate=baud_rate)


# --------------------------------------------------------------------------- #
# baglanti yasam dongusu
# --------------------------------------------------------------------------- #


def test_starts_disconnected_and_connect_reaches_connected() -> None:
    factory = _FakeTransportFactory()
    connection = SerialConnection(_CONFIG, transport_factory=factory)
    assert connection.state is ConnectionState.DISCONNECTED
    connection.connect()
    assert connection.state is ConnectionState.CONNECTED
    assert len(factory.calls) == 1
    assert factory.calls[0][0] is _CONFIG


def test_connect_passes_the_configured_timeout_to_the_factory() -> None:
    factory = _FakeTransportFactory()
    connection = SerialConnection(_CONFIG, timeout_s=0.5, transport_factory=factory)
    connection.connect()
    assert factory.calls[0][1] == 0.5


def test_connect_is_idempotent_and_does_not_reopen_the_transport() -> None:
    factory = _FakeTransportFactory()
    connection = SerialConnection(_CONFIG, transport_factory=factory)
    connection.connect()
    connection.connect()
    assert len(factory.calls) == 1  # ikinci cagri aktarimi tekrar acmadi
    assert connection.state is ConnectionState.CONNECTED


def test_a_failing_transport_raises_and_leaves_the_state_unchanged() -> None:
    factory = _FakeTransportFactory(fail=True)
    connection = SerialConnection(_CONFIG, transport_factory=factory)
    with pytest.raises(OSError, match="port acilamadi"):
        connection.connect()
    assert connection.state is ConnectionState.DISCONNECTED


def test_config_property_exposes_the_validated_config() -> None:
    connection = SerialConnection(_CONFIG, transport_factory=_FakeTransportFactory())
    assert connection.config is _CONFIG


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="timeout_s pozitif olmali"):
        SerialConnection(_CONFIG, timeout_s=0.0, transport_factory=_FakeTransportFactory())


# --------------------------------------------------------------------------- #
# kapatma kaynagi serbest birakir
# --------------------------------------------------------------------------- #


def test_disconnect_closes_the_transport() -> None:
    factory = _FakeTransportFactory()
    connection = SerialConnection(_CONFIG, transport_factory=factory)
    connection.connect()
    transport = factory.transports[0]
    assert not transport.closed

    connection.disconnect()
    assert transport.closed
    assert connection.state is ConnectionState.DISCONNECTED


def test_disconnect_before_connect_is_a_no_op() -> None:
    factory = _FakeTransportFactory()
    connection = SerialConnection(_CONFIG, transport_factory=factory)
    connection.disconnect()
    assert connection.state is ConnectionState.DISCONNECTED
    assert factory.calls == []


def test_disconnect_is_idempotent_and_closes_only_once() -> None:
    factory = _FakeTransportFactory()
    connection = SerialConnection(_CONFIG, transport_factory=factory)
    connection.connect()
    transport = factory.transports[0]

    connection.disconnect()
    connection.disconnect()
    assert connection.state is ConnectionState.DISCONNECTED
    # Ikinci disconnect() close()'u tekrar cagirmadi (transport zaten None'a cekildi).
    assert transport.closed


def test_reconnecting_after_disconnect_opens_a_new_transport() -> None:
    factory = _FakeTransportFactory()
    connection = SerialConnection(_CONFIG, transport_factory=factory)
    connection.connect()
    connection.disconnect()
    connection.connect()
    assert len(factory.calls) == 2
    assert len(factory.transports) == 2
    assert factory.transports[0].closed
    assert not factory.transports[1].closed


# --------------------------------------------------------------------------- #
# pyserial kurulu degil - gercek (taklitsiz) dogrulama
# --------------------------------------------------------------------------- #


def test_the_default_transport_factory_explains_the_missing_pyserial_dependency() -> None:
    """`pyserial` bu ortamda gerçekten kurulu değil; taklit edilmiyor."""
    connection = SerialConnection(_CONFIG)  # transport_factory verilmedi -> onta­nimli
    with pytest.raises(RuntimeError, match=r'pip install -e "\.\[live\]"'):
        connection.connect()
    assert connection.state is ConnectionState.DISCONNECTED
