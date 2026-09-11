"""Serial port ayarı ve bağlantısı — `F5-009`.

Port adı ve hız **bağlantı kurulmadan önce** doğrulanır (`SerialPortConfig`);
gerçek donanım olmadan da test edilebilir. Gerçek port I/O `pyserial`
üzerinden yapılır (isteğe bağlı `live` ekstrası, `pip install -e ".[live]"`)
— bu geliştirme ortamında kurulu **değildir**; `connect()` bu durumda açık
bir hata verir. Testler `transport_factory` enjekte ederek gerçek
donanım/`pyserial` olmadan bağlantı yaşam döngüsünü ve kaynak serbest
bırakmayı doğrular — `FileReplaySource`'un `sleep`/`clock_ns` enjeksiyonuyla
aynı ilke.

Çerçeve sınırı ve zaman aşımı işleyişi `F5-010`'un işi; bu modülde henüz
okuma döngüsü yoktur.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sonar_analyzer.io.live.connection_state_machine import ConnectionStateMachine
from sonar_analyzer.io.live.protocol import ConnectionState

#: Yaygın donanımda desteklenen standart baud hızları.
STANDARD_BAUD_RATES: frozenset[int] = frozenset(
    {
        110,
        300,
        600,
        1200,
        2400,
        4800,
        9600,
        14400,
        19200,
        38400,
        57600,
        115200,
        128000,
        230400,
        256000,
        460800,
        921600,
    }
)

_WINDOWS_PORT_PATTERN = re.compile(r"COM\d+", re.IGNORECASE)
_POSIX_PORT_PATTERN = re.compile(r"/dev/(tty|cu)[A-Za-z0-9.]+")


@dataclass(frozen=True)
class SerialPortConfig:
    """Bağlantı kurulmadan önce doğrulanan port adı ve hız."""

    port: str
    baud_rate: int

    def __post_init__(self) -> None:
        if not self.port.strip():
            raise ValueError("Port adi bos olamaz")
        pattern = _WINDOWS_PORT_PATTERN if sys.platform == "win32" else _POSIX_PORT_PATTERN
        if not pattern.fullmatch(self.port):
            expected = "COMx" if sys.platform == "win32" else "/dev/ttyXxx veya /dev/cu.Xxx"
            raise ValueError(f"Port adi '{expected}' bicimini izlemeli: {self.port!r}")
        if self.baud_rate not in STANDARD_BAUD_RATES:
            raise ValueError(
                f"Desteklenmeyen baud hizi: {self.baud_rate} "
                f"(standart degerler: {sorted(STANDARD_BAUD_RATES)})"
            )


@runtime_checkable
class SerialTransport(Protocol):
    """`SerialConnection`'ın bağlı olduğu ham bayt aktarımı — `pyserial.Serial` ile uyumlu."""

    def read(self, size: int = 1, /) -> bytes: ...

    def write(self, data: bytes, /) -> int | None: ...

    def close(self) -> None: ...


TransportFactory = Callable[[SerialPortConfig, float], SerialTransport]


def _open_pyserial_transport(config: SerialPortConfig, timeout_s: float) -> SerialTransport:
    """Öntanımlı üretici: `pyserial` üzerinden gerçek portu açar.

    `pyserial` kurulu değilse `RuntimeError` — sessizce yutulmaz, ne
    eksik olduğu ve nasıl kurulacağı açıkça söylenir (`app.py`'deki
    PySide6 eksikliği mesajıyla aynı üslup).
    """
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError(
            'Serial port destegi kurulu degil. Kurulum:\n    pip install -e ".[live]"\n'
            f"Ayrinti: {exc}"
        ) from exc
    return serial.Serial(port=config.port, baudrate=config.baud_rate, timeout=timeout_s)


class SerialConnection:
    """Bir seri porta bağlanır — `docs/live/protocol-contract.md` §3.3."""

    def __init__(
        self,
        config: SerialPortConfig,
        *,
        timeout_s: float = 0.2,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError(f"timeout_s pozitif olmali: {timeout_s}")
        self._config = config
        self._timeout_s = timeout_s
        self._transport_factory = transport_factory or _open_pyserial_transport
        self._machine = ConnectionStateMachine()
        self._transport: SerialTransport | None = None

    @property
    def config(self) -> SerialPortConfig:
        return self._config

    @property
    def state(self) -> ConnectionState:
        return self._machine.state

    def connect(self) -> None:
        """Zaten bağlıysa etkisizdir. Port açılamazsa hata **yükselir**, durum değişmez."""
        if self._machine.state is ConnectionState.CONNECTED:
            return
        transport = self._transport_factory(self._config, self._timeout_s)
        self._transport = transport
        self._machine.request_connect()
        self._machine.established()

    def disconnect(self) -> None:
        """Aktarımı kapatır ve kaynağı bırakır. Zaten kopuksa etkisiz."""
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._machine.disconnect()
