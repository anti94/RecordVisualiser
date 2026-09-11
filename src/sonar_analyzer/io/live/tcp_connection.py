"""TCP bağlantı ve okuma akışı — `F5-007`.

Yerel bir sunucuya `socket.SOCK_STREAM` ile **istemci** olarak bağlanır ve
ham bayt akışını okur. `docs/live/protocol-contract.md` §3.2: TCP bir bayt
akışıdır, datagram sınırı yoktur — çerçeve sınırı (uzunluk önekiyle
birleştirme/ayırma) burada **yapılmaz**, `F5-008`'in işidir. Bu, `F5-005`/
`F5-006`'nın UDP tarafındaki "ham alım / çözüm" ayrımıyla aynı ilke.

EOF (karşı taraf **düzgünce** kapattı: `recv()` boş bayt döner) ile bağlantı
hatası (reset, soket kapalı) ayrı durumlara geçer — sözleşmenin "Bağlantı
durum makinesi" bölümüyle (`F5-002`) tutarlı: EOF temiz bir kapanıştır
(`DISCONNECTED`), hata toparlanma adayıdır (`RECONNECTING`).
"""

from __future__ import annotations

import socket
from collections.abc import Iterator

from sonar_analyzer.io.live.connection_state_machine import ConnectionStateMachine
from sonar_analyzer.io.live.protocol import ConnectionState

DEFAULT_RECV_CHUNK_BYTES = 65_536


class TcpConnection:
    """`socket.SOCK_STREAM` üzerinden bir sunucuya bağlanıp ham bayt okur."""

    def __init__(self, host: str, port: int, *, timeout_s: float = 0.2) -> None:
        if timeout_s <= 0:
            raise ValueError(f"timeout_s pozitif olmali: {timeout_s}")
        self._host = host
        self._port = port
        self._timeout_s = timeout_s
        self._machine = ConnectionStateMachine()
        self._socket: socket.socket | None = None

    @property
    def state(self) -> ConnectionState:
        return self._machine.state

    def connect(self) -> None:
        """Zaten bağlıysa etkisizdir. Sunucu yoksa/reddederse `OSError` yükselir.

        Başarısız bir bağlanma denemesi durumu **değiştirmez** — çağıran
        yeniden deneyebilir; `LiveSource.connect()` sözleşmesi hatayı
        yutmaz (`F1-017`).
        """
        if self._machine.state is ConnectionState.CONNECTED:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self._timeout_s)
        try:
            sock.connect((self._host, self._port))
        except OSError:
            sock.close()
            raise
        self._socket = sock
        self._machine.request_connect()
        self._machine.established()

    def disconnect(self) -> None:
        """Soketi kapatır. Zaten kopuksa etkisiz.

        Başka bir iş parçacığı o an `read_chunks()` içinde `recv()`'de
        bloke olmuşsa, soketin kapatılması o çağrıyı `OSError` ile keser.
        """
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._machine.disconnect()

    def read_chunks(self) -> Iterator[bytes]:
        """Bağlı olduğu sürece gelen ham bayt parçalarını verir.

        Karşı taraf **düzgünce** kapatırsa (`recv()` boş bayt döner) EOF
        sayılır: soket kapatılır, durum `DISCONNECTED`'e geçer, üretici
        sessizce biter. Bağlantı hatası (reset, kapalı soket) `RECONNECTING`'e
        geçer — otomatik toparlanma adayı (plan Bölüm 13); yeniden
        `connect()` çağırmak çağıranın işidir.
        """
        while self._machine.state.is_active and self._socket is not None:
            try:
                chunk = self._socket.recv(DEFAULT_RECV_CHUNK_BYTES)
            except socket.timeout:
                continue
            except OSError:
                self._on_connection_error()
                return
            if chunk == b"":
                self._on_eof()
                return
            yield chunk

    def _on_eof(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._machine.disconnect()

    def _on_connection_error(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._machine.connection_lost()
