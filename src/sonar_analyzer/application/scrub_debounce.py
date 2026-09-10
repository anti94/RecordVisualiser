"""Scrubbing sorgularını coalesce eden debouncer — `F3-060`.

Saf Python: Qt yok, `GUI olmadan` doğrulanır. GUI bir zamanlayıcı ile
`poll(now)` çağırır ve asıl (pahalı) sorguyu yalnızca bir yük dönünce
yürütür.

Davranış: **leading + trailing** debounce.

* Boştaki ilk `submit` hemen çalıştırılır (yük geri döner) — kullanıcı
  anında geri bildirim alır.
* Bir "seri" (hızlı sürükleme) içindeki sonraki `submit`'ler beklemeye
  alınır; yalnız **son** yük, `quiet_period_s` kadar sessizlik geçince
  `poll` ile döner. Aradaki konumlar için sorgu yapılmaz.

Ayrıca her verilen sorgu bir **token** alır (`begin_query`). Sorgu
sonucu geldiğinde `is_current(token)` yalnızca daha yeni bir sorgu
başlatılmadıysa `True` döner; böylece geç gelen eski bir sonuç
görünümü ezmez.
"""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class ScrubDebouncer(Generic[T]):
    """Sürükleme yüklerini coalesce eder; eski sorgu sonucunu ayırt eder."""

    def __init__(self, quiet_period_s: float = 0.12) -> None:
        if quiet_period_s < 0.0:
            raise ValueError(f"quiet_period_s negatif olamaz: {quiet_period_s}")
        self._quiet_period_s = quiet_period_s
        self._pending: T | None = None
        self._has_pending = False
        self._pending_since = 0.0
        self._last_run_at = float("-inf")
        self._issued = 0
        self._latest_token = 0

    @property
    def quiet_period_s(self) -> float:
        return self._quiet_period_s

    @property
    def has_pending(self) -> bool:
        return self._has_pending

    def submit(self, payload: T, *, now: float) -> T | None:
        """Yeni bir scrub konumu bildirir.

        Boştaysa (son çalıştırmadan bu yana `quiet_period_s` geçmiş ve
        bekleyen yük yok) yükü **hemen** döndürür; çağıran sorguyu
        şimdi yürütmelidir. Seri içindeyse `None` döndürür ve yükü
        `poll` için bekletir (önceki bekleyeni ezerek).
        """
        if not self._has_pending and now - self._last_run_at >= self._quiet_period_s:
            self._last_run_at = now
            return payload
        self._pending = payload
        self._has_pending = True
        self._pending_since = now
        return None

    def poll(self, now: float) -> T | None:
        """Bekleyen yükü, sessizlik süresi dolduysa döndürür; yoksa `None`."""
        if not self._has_pending:
            return None
        if now - self._pending_since < self._quiet_period_s:
            return None
        self._last_run_at = now
        return self._take()

    def flush(self, now: float) -> T | None:
        """Bekleyen yükü sessizliği beklemeden döndürür (sürükleme bitti)."""
        if not self._has_pending:
            return None
        self._last_run_at = now
        return self._take()

    def cancel(self) -> None:
        """Bekleyen yükü atar (kayıt kapandı, kanal değişti vb.)."""
        self._pending = None
        self._has_pending = False

    def begin_query(self) -> int:
        """Yürütülmek üzere olan sorguya artan bir token verir."""
        self._issued += 1
        self._latest_token = self._issued
        return self._latest_token

    def is_current(self, token: int) -> bool:
        """`token` en son verilen sorgununsa `True` (daha yenisi yok)."""
        return token == self._latest_token

    def _take(self) -> T | None:
        payload = self._pending
        self._pending = None
        self._has_pending = False
        return payload
