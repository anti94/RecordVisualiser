"""Burst, kayıp ve sıra dışı paket simülatörü — `F5-036`.

Kabul: **Her senaryo seed ile tekrar üretilebilir.**

Canlı katmanın dayanıklılığı (kuyruk sınırı, sıra izleyici, yeniden
bağlanma) ancak bozuk bir akışla sınanabilir. Bu modül sağlam bir
kaynağın önüne geçip akışı **kasıtlı olarak** bozar:

* **kayıp** — paket hiç gönderilmez (ağdaki düşme),
* **sıra dışı** — paket bekletilip birkaç paket sonra gönderilir,
* **tekrar** — aynı paket iki kez gönderilir,
* **burst** — paketler öbekler hâlinde, aralarında duraklama ile gelir.

Tekrar üretilebilirliğin kaynağı tek bir `random.Random(seed)`'dir.
Modül **global** rastgeleliğe (`random.random()`) hiç dokunmaz; global
durum başka bir testin çağrısıyla kayabilir ve aynı seed farklı sonuç
verirdi. Zaman da enjekte edilir (`sleep`), böylece bir senaryo gerçek
saniyeler beklemeden tekrarlanabilir.

Bozulan her paket **sayılır** (`ImpairmentStats`): hangi senaryonun ne
kadar bozduğu görünmezse, bir testin gerçekten kayıp üretip üretmediği
bilinemezdi.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, replace

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveSource, LiveStats

#: Öntanımlı seed — açıkça verilmese de koşu tekrar üretilebilir olsun.
DEFAULT_SEED = 20260911


@dataclass(frozen=True)
class ImpairmentProfile:
    """Akışın nasıl bozulacağı. Oranlar `[0, 1]` aralığında olasılıktır."""

    loss_ratio: float = 0.0
    reorder_ratio: float = 0.0
    #: Sıra dışı bırakılan paket kaç paket sonra salınır.
    reorder_depth: int = 3
    duplicate_ratio: float = 0.0
    #: Kaç paket arka arkaya gönderilir; `1` düz akış demektir.
    burst_size: int = 1
    #: İki burst arasındaki duraklama (saniye).
    burst_pause_s: float = 0.0

    def __post_init__(self) -> None:
        for name in ("loss_ratio", "reorder_ratio", "duplicate_ratio"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} [0, 1] araliginda olmali: {value}")
        if self.reorder_depth < 1:
            raise ValueError(f"reorder_depth pozitif olmali: {self.reorder_depth}")
        if self.burst_size < 1:
            raise ValueError(f"burst_size pozitif olmali: {self.burst_size}")
        if self.burst_pause_s < 0:
            raise ValueError(f"burst_pause_s negatif olamaz: {self.burst_pause_s}")

    @property
    def is_clean(self) -> bool:
        """Hiçbir bozulma yok mu? (Karşılaştırma koşuları için.)"""
        return self.loss_ratio == 0.0 and self.reorder_ratio == 0.0 and self.duplicate_ratio == 0.0


@dataclass(frozen=True)
class ImpairmentStats:
    """Bir koşuda neyin ne kadar bozulduğu."""

    consumed: int = 0
    emitted: int = 0
    dropped: int = 0
    reordered: int = 0
    duplicated: int = 0

    @property
    def loss_ratio(self) -> float:
        return 0.0 if self.consumed == 0 else self.dropped / self.consumed


def _due(held: list[tuple[int, LivePacket]], position: int) -> Iterator[LivePacket]:
    """Salınma zamanı gelmiş paketleri verir ve bekleyenlerden düşürür."""
    ready = [entry for entry in held if entry[0] <= position]
    for entry in ready:
        held.remove(entry)
    for _due_at, packet in ready:
        yield packet


class ImpairedSource:
    """Bir canlı kaynağın akışını seed'e bağlı olarak bozar — `F5-036`.

    `LiveSource` sözleşmesini karşılar; tüketici tarafında gerçek bir
    kaynaktan ayırt edilemez, bu yüzden kuyruk/izleyici/arayüz kodu hiç
    değişmeden bozuk akışla sınanabilir.
    """

    def __init__(
        self,
        upstream: LiveSource,
        profile: ImpairmentProfile | None = None,
        *,
        seed: int = DEFAULT_SEED,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._upstream = upstream
        self._profile = profile if profile is not None else ImpairmentProfile()
        self._seed = seed
        self._sleep = sleep
        self._stats = ImpairmentStats()

    # -- LiveSource sozlesmesi -------------------------------------------

    @property
    def state(self) -> ConnectionState:
        return self._upstream.state

    def channels(self) -> Sequence[ChannelMetadata]:
        return self._upstream.channels()

    def stats(self) -> LiveStats:
        return self._upstream.stats()

    def connect(self) -> None:
        self._upstream.connect()

    def disconnect(self) -> None:
        self._upstream.disconnect()

    # -- bozma -----------------------------------------------------------

    @property
    def profile(self) -> ImpairmentProfile:
        return self._profile

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def impairment_stats(self) -> ImpairmentStats:
        """Son koşuda neyin ne kadar bozulduğu."""
        return self._stats

    def packets(self) -> Iterator[LivePacket]:
        """Bozulmuş akışı üretir. Aynı seed + aynı girdi = aynı çıktı."""
        return self.impair(self._upstream.packets())

    def impair(self, packets: Iterable[LivePacket]) -> Iterator[LivePacket]:
        """Verilen paket dizisini profile göre bozar.

        Sıra dışı bırakılan paketler **kaybolmaz**: `reorder_depth` paket
        sonra ya da akış biterken mutlaka salınır. Kaybolsalardı "sıra
        dışı" ile "kayıp" ayırt edilemezdi ve test ikisini karıştırırdı.
        """
        rng = random.Random(self._seed)
        profile = self._profile
        self._stats = ImpairmentStats()
        held: list[tuple[int, LivePacket]] = []
        position = 0
        in_burst = 0

        for packet in packets:
            self._count(consumed=1)

            # Dusen paket bile olsa sira ilerler; yoksa tek bir kayip
            # bekleyen paketleri sonsuza dek kilitlerdi.
            position += 1

            if profile.loss_ratio and rng.random() < profile.loss_ratio:
                self._count(dropped=1)
                for released in _due(held, position):
                    self._count(emitted=1)
                    yield released
                continue

            if profile.reorder_ratio and rng.random() < profile.reorder_ratio:
                held.append((position + profile.reorder_depth, packet))
                self._count(reordered=1)
                continue

            # Tekrar eden paket gercekten AYNI nesnedir; kopyalanip
            # degistirilmis bir paket bambaska bir senaryo olurdu.
            copies = 1
            if profile.duplicate_ratio and rng.random() < profile.duplicate_ratio:
                copies = 2
                self._count(duplicated=1)

            for _ in range(copies):
                self._count(emitted=1)
                yield packet
                in_burst += 1
                if in_burst >= profile.burst_size:
                    in_burst = 0
                    if profile.burst_pause_s:
                        self._sleep(profile.burst_pause_s)

            for released in _due(held, position):
                self._count(emitted=1)
                yield released

        # Akis bitti: bekleyenler MUTLAKA salinir — sira disi birakilan
        # paket kaybolsaydi "sira disi" ile "kayip" ayirt edilemezdi.
        for _due_at, packet in held:
            self._count(emitted=1)
            yield packet
        held.clear()

    def _count(
        self,
        *,
        consumed: int = 0,
        emitted: int = 0,
        dropped: int = 0,
        reordered: int = 0,
        duplicated: int = 0,
    ) -> None:
        current = self._stats
        self._stats = replace(
            current,
            consumed=current.consumed + consumed,
            emitted=current.emitted + emitted,
            dropped=current.dropped + dropped,
            reordered=current.reordered + reordered,
            duplicated=current.duplicated + duplicated,
        )
