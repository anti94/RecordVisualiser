"""Serial port ayarı, bağlantısı ve ham okuma — `F5-009`, `F5-010`.

Port adı ve hız **bağlantı kurulmadan önce** doğrulanır (`SerialPortConfig`);
gerçek donanım olmadan da test edilebilir. Gerçek port I/O `pyserial`
üzerinden yapılır (isteğe bağlı `live` ekstrası, `pip install -e ".[live]"`)
— bu geliştirme ortamında kurulu **değildir**; `connect()` bu durumda açık
bir hata verir. Testler `transport_factory` enjekte ederek gerçek
donanım/`pyserial` olmadan bağlantı yaşam döngüsünü ve kaynak serbest
bırakmayı doğrular — `FileReplaySource`'un `sleep`/`clock_ns` enjeksiyonuyla
aynı ilke.

Çerçeve sınırı (`SYNC` deseni, CRC32) `F5-010`'un ayrı çerçeve okuyucusunun
(`serial_live_source.py`) işidir; burada yalnız ham bayt okuma ve
çerçeve-düzeyinde sessizlik zaman aşımının **uygulanması** (`report_silence_
timeout`) vardır — "1000 ms geçti mi" kararı çerçeveleri anlayan katmana
aittir.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterator
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

    def read_chunks(self, *, chunk_bytes: int = 4096) -> Iterator[bytes]:
        """Bağlı olduğu sürece okunan bayt parçalarını verir — `F5-010`.

        `pyserial`'in zaman aşımı davranışı TCP'den **farklıdır**: süre
        dolduğunda `read()` boş bayt döner, bu EOF değildir ("şimdilik
        veri yok" demektir). Bu yüzden boş dönüş de **yayınlanır** — üst
        katmanın (çerçeve düzeyinde sessizlik süresi, `F5-010`) kendi
        zaman aşımı muhasebesini tutabilmesi için bir "nabız" görevi
        görür. Gerçek bir aktarım hatası (ör. cihaz çıkarıldı) `OSError`
        fırlatır; bu durumda bağlantı `RECONNECTING`'e düşer.
        """
        while self._machine.state.is_active and self._transport is not None:
            try:
                chunk = self._transport.read(chunk_bytes)
            except OSError:
                self._on_transport_error()
                return
            yield chunk  # bos olabilir; bu normaldir, akisi bitirmez

    def report_silence_timeout(self) -> None:
        """Çerçeve düzeyinde sessizlik zaman aşımını bildirir → `RECONNECTING`.

        `SerialConnection` çerçeveleri anlamaz; "son geçerli çerçeveden
        beri 1000 ms geçti" kararı `F5-010`'un çerçeve okuyucusuna aittir
        — bu yalnız o kararın sonucunu uygular: aktarım kapatılır (port
        kapanır, `docs/live/protocol-contract.md` §3.3: "port kapatılıp
        yeniden açılır"), durum bir bağlantı kaybı gibi `RECONNECTING`'e
        geçer.
        """
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._machine.connection_lost()

    def _on_transport_error(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._machine.connection_lost()
