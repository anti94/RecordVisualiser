"""UDP datagram alıcısı — `F5-005`.

Yerel bir adrese bağlanıp ham UDP datagramlarını verir. Bu sınıf
`LiveSource` sözleşmesini **karşılamaz** — yalnız bayt alır;
`docs/live/protocol-contract.md`'nin `LiveWireHeader`'ına göre çözüm ve
`LivePacket` üretimi `F5-006`'nın işidir. Katman ayrımı kasıtlı: soket
ömrü ile tel çözümlemesi bağımsız test edilebilir olmalı (aynı ilke
`F5-001`'in "bu belge yalnız zarfı sabitler" sınırıyla tutarlı).
"""

from __future__ import annotations

import socket
from collections.abc import Iterator

from sonar_analyzer.io.live.connection_state_machine import ConnectionStateMachine
from sonar_analyzer.io.live.protocol import ConnectionState

#: Tek bir UDP datagramının olabilecek en büyük boyutu (IPv4, teorik üst sınır).
MAX_UDP_DATAGRAM_BYTES = 65_507


class UdpDatagramReceiver:
    """`socket.SOCK_DGRAM` üzerinden yerel bir porta bağlanıp datagram alır."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, timeout_s: float = 0.2) -> None:
        if timeout_s <= 0:
            raise ValueError(f"timeout_s pozitif olmali: {timeout_s}")
        self._host = host
        self._port = port
        self._timeout_s = timeout_s
        self._machine = ConnectionStateMachine()
        self._socket: socket.socket | None = None
        self._received = 0

    @property
    def state(self) -> ConnectionState:
        return self._machine.state

    @property
    def received_count(self) -> int:
        return self._received

    @property
    def local_port(self) -> int:
        """Gerçekten bağlanılan port (`port=0` verildiyse işletim sistemi seçer)."""
        if self._socket is None:
            raise RuntimeError("local_port icin once connect() cagrilmali")
        return int(self._socket.getsockname()[1])

    def connect(self) -> None:
        """Zaten bağlıysa etkisizdir (`LiveSource.connect()` sözleşmesi, `F1-017`)."""
        if self._machine.state is ConnectionState.CONNECTED:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self._host, self._port))
        except OSError:
            sock.close()
            raise
        sock.settimeout(self._timeout_s)
        self._socket = sock
        self._machine.request_connect()
        self._machine.established()

    def disconnect(self) -> None:
        """Soketi kapatır ve portu serbest bırakır. Zaten kopuksa etkisiz.

        Başka bir iş parçacığı o an `datagrams()` içinde `recvfrom()`'da
        bloke olmuşsa, soketin kapatılması o çağrıyı `OSError` ile keser —
        döngü yeni datagram beklemeden hemen sonlanır.
        """
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._machine.disconnect()

    def datagrams(self) -> Iterator[bytes]:
        """Bağlı olduğu sürece gelen ham datagramları verir.

        `timeout_s` içinde datagram gelmezse döngü yalnız bağlantı/soket
        durumunu **tekrar kontrol etmek için** döner — bu, `disconnect()`'in
        başka bir iş parçacığından çağrılabilmesini sağlar (F5-002'nin
        durum makinesiyle aynı ilke: dışarıdan tetiklenen olaylara açık).
        """
        while self._machine.state.is_active and self._socket is not None:
            try:
                payload, _address = self._socket.recvfrom(MAX_UDP_DATAGRAM_BYTES)
            except socket.timeout:
                continue
            except OSError:
                return
            self._received += 1
            yield payload
