"""Sınırlı kuyruk ve drop politikası — `F5-016`.

Plan Bölüm 13: "Backpressure/drop policy tanımı". Kuyruk, paketleri üreten
I/O iş parçacığı ile onları tüketen (çizim/işleme) taraf arasında durur.
Tüketici yetişemezse **bir şey kaybolmak zorundadır**; buradaki sözleşme
o kaybın ne olduğunu ve nasıl sayıldığını belirler:

- **`DROP_OLDEST`** (öntanımlı) — en eski paket düşer, en yenisi girer.
  Canlı görünümün varsayılanı budur: `docs/live/protocol-contract.md`
  §3.1 zaten "canlı görünüm eski veriyi beklemez" diyor.
- **`DROP_NEWEST`** — kuyruktakiler korunur, gelen paket reddedilir.
  Sürekliliğin tazelikten önemli olduğu tüketiciler için.
- **`BLOCK`** — gerçek backpressure: üretici yer açılana kadar bekler
  (zaman aşımıyla). Kayıt (`F5-025`+) gibi veri kaybını kabul etmeyen
  tüketiciler için.

Hangi politika seçilirse seçilsin iki değişmez korunur: **derinlik
`maxsize`'ı asla aşmaz** ve **düşen paket sayısı raporlanır** — sessizce
kaybolan veri yoktur.

Kuyruk iş parçacığı güvenlidir (`threading.Condition`): üretici I/O
parçacığından, tüketici arayüz parçacığından çağırabilir.
"""

from __future__ import annotations

import threading
from collections import deque
from enum import Enum

from sonar_analyzer.io.live.protocol import LivePacket, LiveStats


class DropPolicy(str, Enum):
    """Kuyruk dolduğunda ne olacağı."""

    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"


class BoundedPacketQueue:
    """Sabit sınırlı, iş parçacığı güvenli paket kuyruğu."""

    def __init__(
        self,
        maxsize: int,
        *,
        policy: DropPolicy = DropPolicy.DROP_OLDEST,
        block_timeout_s: float = 1.0,
    ) -> None:
        if maxsize < 1:
            raise ValueError(f"maxsize pozitif olmali: {maxsize}")
        if block_timeout_s <= 0:
            raise ValueError(f"block_timeout_s pozitif olmali: {block_timeout_s}")
        self._maxsize = maxsize
        self._policy = policy
        self._block_timeout_s = block_timeout_s
        self._items: deque[LivePacket] = deque()
        self._condition = threading.Condition()
        self._dropped = 0
        self._accepted = 0
        self._peak_depth = 0

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def policy(self) -> DropPolicy:
        return self._policy

    @property
    def depth(self) -> int:
        with self._condition:
            return len(self._items)

    @property
    def peak_depth(self) -> int:
        """Gördüğü en yüksek derinlik — "sınır aşılmadı" iddiasının ölçüsü."""
        with self._condition:
            return self._peak_depth

    @property
    def dropped_total(self) -> int:
        with self._condition:
            return self._dropped

    @property
    def accepted_total(self) -> int:
        """Kuyruğa **giren** paket sayısı — politikaya bağlıdır.

        `DROP_OLDEST`'te gelen her paket girer (ve yer açmak için eski bir
        paket düşer), bu yüzden `accepted + dropped` bir korunum yasası
        **değildir**. Korunum yasası her politikada şudur:
        `kuyruktaki + tüketilen + düşen == üretilen`.
        """
        with self._condition:
            return self._accepted

    def put(self, packet: LivePacket) -> bool:
        """Paketi kuyruğa koyar. Kabul edildiyse `True`, düştüyse `False`.

        `BLOCK` politikasında yer açılana kadar (en çok `block_timeout_s`)
        bekler; süre dolarsa paket düşer ve `False` döner.
        """
        with self._condition:
            if len(self._items) >= self._maxsize:
                if self._policy is DropPolicy.DROP_NEWEST:
                    self._dropped += 1
                    return False
                if self._policy is DropPolicy.BLOCK:
                    got_space = self._condition.wait_for(
                        lambda: len(self._items) < self._maxsize, timeout=self._block_timeout_s
                    )
                    if not got_space:
                        self._dropped += 1
                        return False
                else:  # DROP_OLDEST
                    self._items.popleft()
                    self._dropped += 1

            self._items.append(packet)
            self._accepted += 1
            self._peak_depth = max(self._peak_depth, len(self._items))
            self._condition.notify_all()
            return True

    def get(self, timeout_s: float | None = None) -> LivePacket | None:
        """Sıradaki paketi (FIFO) alır; kuyruk boşsa `None`.

        `timeout_s` verilirse o süre kadar bekler — tüketicinin meşgul
        döngüde dönmesi gerekmez.
        """
        with self._condition:
            if not self._items and timeout_s is not None:
                self._condition.wait_for(lambda: bool(self._items), timeout=timeout_s)
            if not self._items:
                return None
            packet = self._items.popleft()
            self._condition.notify_all()
            return packet

    def drain(self) -> list[LivePacket]:
        """Kuyruktaki her şeyi FIFO sırayla alır ve kuyruğu boşaltır."""
        with self._condition:
            drained = list(self._items)
            self._items.clear()
            self._condition.notify_all()
            return drained

    def stats(self, *, received_packets: int = 0, last_sequence_no: int | None = None) -> LiveStats:
        """`LiveStats`'in kuyrukla ilgili alanlarını doldurur (`F1-017`)."""
        with self._condition:
            return LiveStats(
                received_packets=received_packets,
                dropped_packets=self._dropped,
                queue_depth=len(self._items),
                last_sequence_no=last_sequence_no,
            )

    def clear(self) -> None:
        """Kuyruğu ve sayaçları sıfırlar."""
        with self._condition:
            self._items.clear()
            self._dropped = 0
            self._accepted = 0
            self._peak_depth = 0
            self._condition.notify_all()
