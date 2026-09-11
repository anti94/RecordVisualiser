"""Sınırlı otomatik yeniden bağlanma — `F5-017`.

Plan Bölüm 13: "Bağlantı kesilince otomatik yeniden bağlanma seçeneği".
İki kural bu modülün varlık nedenidir:

1. **Denemeler görünürdür.** Her deneme (`ReconnectAttempt`) numarası,
   beklenen gecikmesi ve sonucuyla kaydedilir — arayüz "3/5. deneme,
   4 sn sonra" diyebilsin diye. Sessizce arka planda dönen bir yeniden
   bağlanma döngüsü, kullanıcının neden bağlanamadığını bilememesi demek.
2. **Kullanıcı durdurunca yeniden bağlantı başlamaz.** `stop()` çağrıldıysa
   ne yeni bir deneme başlar ne de sürmekte olan bekleme yeni bir denemeye
   dönüşür. Kullanıcının açık "Disconnect" eylemini otomatik bir yeniden
   bağlanmanın geçersiz kılması gerçek bir hata olurdu.

Deneme sayısı **sınırlıdır** (`max_attempts`): sonsuza kadar deneyen bir
döngü, bağlantının gerçekten öldüğünü hiçbir zaman raporlamaz.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sonar_analyzer.io.live.protocol import ConnectionState


@runtime_checkable
class Reconnectable(Protocol):
    """Yeniden bağlanma denetleyicisinin ihtiyaç duyduğu en küçük arayüz.

    Dört canlı adaptör de (`FileReplaySource`, `UdpLiveSource`,
    `TcpLiveSource`, `SerialLiveSource`) bunu yapısal olarak karşılar.
    """

    @property
    def state(self) -> ConnectionState: ...

    def connect(self) -> None: ...


@dataclass(frozen=True)
class ReconnectPolicy:
    """Kaç kez, ne aralıkla denenecek."""

    max_attempts: int = 5
    initial_delay_s: float = 0.5
    backoff_factor: float = 2.0
    max_delay_s: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts pozitif olmali: {self.max_attempts}")
        if self.initial_delay_s < 0:
            raise ValueError(f"initial_delay_s negatif olamaz: {self.initial_delay_s}")
        if self.backoff_factor < 1.0:
            raise ValueError(f"backoff_factor en az 1.0 olmali: {self.backoff_factor}")
        if self.max_delay_s < self.initial_delay_s:
            raise ValueError(
                f"max_delay_s ({self.max_delay_s}) initial_delay_s "
                f"({self.initial_delay_s}) altinda olamaz"
            )

    def delay_for(self, attempt: int) -> float:
        """`attempt` (1'den başlar) öncesi beklenecek süre — üstel, tavanlı."""
        if attempt < 1:
            raise ValueError(f"attempt 1'den baslar: {attempt}")
        delay = self.initial_delay_s * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay_s)


@dataclass(frozen=True)
class ReconnectAttempt:
    """Tek bir denemenin görünür kaydı."""

    number: int
    delay_s: float
    succeeded: bool
    error: str | None = None


class ReconnectController:
    """Bağlantı koptuğunda sınırlı sayıda, görünür yeniden deneme yapar."""

    def __init__(
        self,
        source: Reconnectable,
        policy: ReconnectPolicy | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._source = source
        self._policy = policy if policy is not None else ReconnectPolicy()
        self._sleep = sleep
        self._attempts: list[ReconnectAttempt] = []
        self._stopped = False

    @property
    def policy(self) -> ReconnectPolicy:
        return self._policy

    @property
    def attempts(self) -> tuple[ReconnectAttempt, ...]:
        """Şimdiye kadarki denemeler — arayüzün gösterdiği şey."""
        return tuple(self._attempts)

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self) -> None:
        """Kullanıcı durdurdu: bundan sonra hiçbir deneme başlamaz."""
        self._stopped = True

    def reset(self) -> None:
        """Yeni bir bağlantı oturumu için sayaçları ve durdurma bayrağını temizler."""
        self._attempts.clear()
        self._stopped = False

    def run(self) -> bool:
        """Bağlanana kadar (en çok `max_attempts`) dener. Bağlandıysa `True`.

        Her denemeden **önce** durdurulma denetlenir; kullanıcı beklerken
        durdurursa o bekleme yeni bir denemeye dönüşmez.
        """
        for number in range(1, self._policy.max_attempts + 1):
            if self._stopped:
                return False
            delay = self._policy.delay_for(number)
            if delay:
                self._sleep(delay)
            if self._stopped:  # bekleme sirasinda kullanici durdurmus olabilir
                return False

            try:
                self._source.connect()
            except Exception as exc:
                self._attempts.append(ReconnectAttempt(number, delay, False, f"{exc}"))
                continue

            succeeded = self._source.state is ConnectionState.CONNECTED
            self._attempts.append(ReconnectAttempt(number, delay, succeeded))
            if succeeded:
                return True
        return False
