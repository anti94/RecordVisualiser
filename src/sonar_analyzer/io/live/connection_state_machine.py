"""Bağlantı durum makinesi — `F5-002`.

`F1-017` `ConnectionState`'i tanımladı (`DISCONNECTED`, `CONNECTING`,
`CONNECTED`, `RECONNECTING`, `FAILED`); bu modül aralarındaki **izinli
geçişleri** kurar. `plan.md` Bölüm 13'ün "disconnected, connecting,
connected, degraded, error" listesiyle isim eşlemesi:

- "degraded" → `RECONNECTING` — bağlantı koptu, otomatik toparlanma
  deneniyor (Bölüm 13: "Bağlantı kesilince otomatik yeniden bağlanma
  seçeneği").
- "error" → `FAILED` — toparlanma denemeleri tükendi, kullanıcı
  müdahalesi gerekir.

Bu adaptörlerin (`F5-005`+) I/O döngüsünün **çağıracağı** olaylardır;
GUI'yi veya soketi bilmez.
"""

from __future__ import annotations

from sonar_analyzer.io.live.protocol import ConnectionState

#: `(kaynak, hedef)` — izinli geçişler. Eksik bir çift `transition()`'da reddedilir.
_ALLOWED: frozenset[tuple[ConnectionState, ConnectionState]] = frozenset(
    {
        (ConnectionState.DISCONNECTED, ConnectionState.CONNECTING),
        (ConnectionState.CONNECTING, ConnectionState.CONNECTED),
        (ConnectionState.CONNECTING, ConnectionState.FAILED),
        (ConnectionState.CONNECTED, ConnectionState.RECONNECTING),
        (ConnectionState.RECONNECTING, ConnectionState.CONNECTED),
        (ConnectionState.RECONNECTING, ConnectionState.FAILED),
        (ConnectionState.FAILED, ConnectionState.CONNECTING),
        # Kullanıcı her durumdan bağlantıyı kapatabilir.
        (ConnectionState.CONNECTING, ConnectionState.DISCONNECTED),
        (ConnectionState.CONNECTED, ConnectionState.DISCONNECTED),
        (ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED),
        (ConnectionState.FAILED, ConnectionState.DISCONNECTED),
    }
)

#: `request_connect()` zaten bu durumlardaysa etkisizdir (yeniden istek gereksiz).
_ALREADY_CONNECTING_OR_BETTER = (
    ConnectionState.CONNECTING,
    ConnectionState.CONNECTED,
    ConnectionState.RECONNECTING,
)


class ConnectionStateMachine:
    """`ConnectionState` geçişlerini izinli kümeye göre uygular.

    İzinsiz bir geçiş denemesi durumu **değiştirmez** ve `ValueError` yükseltir
    — sessizce yoksayılan bir hatalı geçiş, tanılamada görünmeyen bir bağlantı
    hatası demektir.
    """

    def __init__(self) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._history: list[ConnectionState] = [self._state]

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def history(self) -> tuple[ConnectionState, ...]:
        """Kurulduğundan beri ziyaret edilen durumlar, sırayla (tanılama)."""
        return tuple(self._history)

    def request_connect(self) -> None:
        """Bağlanma isteği. `DISCONNECTED`/`FAILED` → `CONNECTING`.

        Zaten bağlanıyor/bağlı/toparlanıyorsa etkisizdir (idempotent —
        `LiveSource.connect()`'in F1-017 sözleşmesiyle tutarlı).
        """
        if self._state in _ALREADY_CONNECTING_OR_BETTER:
            return
        self._transition(ConnectionState.CONNECTING)

    def established(self) -> None:
        """El sıkışma tamamlandı. `CONNECTING`/`RECONNECTING` → `CONNECTED`."""
        self._transition(ConnectionState.CONNECTED)

    def connection_lost(self) -> None:
        """Bağlıyken bağlantı koptu → `RECONNECTING` ("degraded", otomatik toparlanma)."""
        self._transition(ConnectionState.RECONNECTING)

    def retries_exhausted(self) -> None:
        """Toparlanma denemeleri tükendi → `FAILED` ("error")."""
        self._transition(ConnectionState.FAILED)

    def disconnect(self) -> None:
        """Kullanıcı bağlantıyı kapatır → `DISCONNECTED`. Zaten kopuksa etkisiz."""
        if self._state is ConnectionState.DISCONNECTED:
            return
        self._transition(ConnectionState.DISCONNECTED)

    def _transition(self, target: ConnectionState) -> None:
        pair = (self._state, target)
        if pair not in _ALLOWED:
            raise ValueError(f"İzinsiz geçiş: {self._state.value} -> {target.value}")
        self._state = target
        self._history.append(target)
