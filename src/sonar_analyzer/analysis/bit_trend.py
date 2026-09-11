"""BIT durum süresi ve değişim trendi — `F4-080`.

Bir BIT testi kayıt boyunca defalarca koşar ve her koşuda bir durum
(`PASS`/`WARN`/`FAIL`/…) üretir. Operatörün sorduğu şey tek tek koşular
değil, **davranış**tır: bu bileşen ne kadar süre FAIL kaldı, kaç kez
durum değiştirdi, ilk arıza ne zaman başladı.

Bu modül bir `BitResult` dizisini o sorulara çevirir:

* **aralık** (`BitInterval`) — durumun sabit kaldığı ardışık koşular tek
  bir aralığa toplanır; aralık bir sonraki **farklı** duruma kadar sürer.
* **değişim** (`transitions`) — iki komşu aralık arasındaki her geçiş.
* **süre** (`duration_for`) — her durumda toplam geçirilen zaman.

**Son aralığın bitişi.** Son koşudan sonra ne olduğunu bilmiyoruz. Bu
yüzden aralığın bitişi çağıranın verdiği `end_ns` ile kapanır (genelde
kaydın sonu); verilmezse son koşunun zamanıdır ve süre **sıfır** olur.
Uydurma bir bitiş zamanı üretilmez — bilinmeyen süre sıfırdır, tahmin
değildir.

Saf Python — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sonar_analyzer.domain.event import BitResult, BitState
from sonar_analyzer.domain.time_range import NS_PER_SECOND, TimeRange


class BitTrendError(ValueError):
    """Trend hesaplanamıyor (ters zaman aralığı vb.)."""


@dataclass(frozen=True)
class BitInterval:
    """Bir bileşenin durumunun sabit kaldığı kesintisiz zaman aralığı."""

    component: str
    test_id: int
    state: BitState
    start_ns: int
    end_ns: int
    #: Bu aralığı oluşturan koşu sayısı.
    run_count: int = 1

    def __post_init__(self) -> None:
        if self.end_ns < self.start_ns:
            raise BitTrendError(
                f"{self.component}: aralık bitişi ({self.end_ns}) başlangıçtan "
                f"({self.start_ns}) küçük olamaz"
            )
        if self.run_count < 1:
            raise BitTrendError(f"{self.component}: koşu sayısı en az 1 olmalı")

    @property
    def duration_ns(self) -> int:
        return self.end_ns - self.start_ns

    @property
    def duration_seconds(self) -> float:
        return self.duration_ns / NS_PER_SECOND

    @property
    def span(self) -> TimeRange:
        return TimeRange(self.start_ns, self.end_ns)

    @property
    def is_failure(self) -> bool:
        return self.state.is_failure


@dataclass(frozen=True)
class BitTransition:
    """İki aralık arasındaki durum değişimi."""

    component: str
    test_id: int
    timestamp_ns: int
    previous: BitState
    current: BitState

    @property
    def became_failure(self) -> bool:
        """Sağlamdan arızaya geçiş mi."""
        return not self.previous.is_failure and self.current.is_failure

    @property
    def recovered(self) -> bool:
        """Arızadan sağlama dönüş mü."""
        return self.previous.is_failure and not self.current.is_failure


@dataclass(frozen=True)
class BitTrend:
    """Tek bir bileşenin kayıt boyunca davranışı."""

    component: str
    test_id: int
    intervals: tuple[BitInterval, ...]
    transitions: tuple[BitTransition, ...]

    @property
    def run_count(self) -> int:
        return sum(interval.run_count for interval in self.intervals)

    @property
    def change_count(self) -> int:
        """Durum kaç kez değişti (ilk durum bir değişim sayılmaz)."""
        return len(self.transitions)

    @property
    def first_state(self) -> BitState | None:
        return self.intervals[0].state if self.intervals else None

    @property
    def last_state(self) -> BitState | None:
        return self.intervals[-1].state if self.intervals else None

    @property
    def total_ns(self) -> int:
        return sum(interval.duration_ns for interval in self.intervals)

    def duration_for(self, state: BitState) -> int:
        """`state` durumunda geçirilen toplam süre (ns)."""
        return sum(interval.duration_ns for interval in self.intervals if interval.state is state)

    def failure_ns(self) -> int:
        """`WARN` ve `FAIL` aralıklarının toplamı."""
        return sum(interval.duration_ns for interval in self.intervals if interval.is_failure)

    def failure_ratio(self) -> float:
        """Arızalı sürenin toplam süreye oranı; süre yoksa 0."""
        total = self.total_ns
        return self.failure_ns() / total if total else 0.0

    def first_failure(self) -> BitInterval | None:
        """İlk arıza aralığı; hiç arıza yoksa `None`."""
        return next((interval for interval in self.intervals if interval.is_failure), None)

    def intervals_in(self, span: TimeRange) -> tuple[BitInterval, ...]:
        """`span` ile kesişen aralıklar."""
        return tuple(
            interval
            for interval in self.intervals
            if interval.start_ns < span.end_ns
            and (span.start_ns < interval.end_ns or interval.duration_ns == 0)
            and interval.end_ns >= span.start_ns
        )


def _sorted_runs(results: Iterable[BitResult]) -> list[BitResult]:
    """Koşuları zamana göre kararlı sıralar (aynı anda gelenler sırasını korur)."""
    return sorted(results, key=lambda item: item.timestamp_ns)


def build_trend(
    results: Sequence[BitResult],
    *,
    end_ns: int | None = None,
) -> BitTrend:
    """Tek bir bileşenin koşularını aralıklara ve değişimlere çevirir.

    `results` **aynı** `test_id`'ye ait olmalıdır; farklı testler
    karıştırılırsa `BitTrendError` yükselir — sessizce birleştirmek
    anlamsız bir trend üretirdi.
    """
    runs = _sorted_runs(results)
    if not runs:
        return BitTrend(component="", test_id=-1, intervals=(), transitions=())

    identifiers = {(item.test_id, item.component) for item in runs}
    if len(identifiers) != 1:
        raise BitTrendError(f"Trend tek bir BIT testi içindir; verilenler: {sorted(identifiers)}")
    test_id, component = next(iter(identifiers))

    closing = runs[-1].timestamp_ns if end_ns is None else end_ns
    if closing < runs[-1].timestamp_ns:
        raise BitTrendError(
            f"{component}: kapanış zamanı ({closing}) son koşudan "
            f"({runs[-1].timestamp_ns}) önce olamaz"
        )

    intervals: list[BitInterval] = []
    start_index = 0
    for index in range(1, len(runs) + 1):
        finished = index == len(runs) or runs[index].state is not runs[start_index].state
        if not finished:
            continue
        first = runs[start_index]
        end = closing if index == len(runs) else runs[index].timestamp_ns
        intervals.append(
            BitInterval(
                component=component,
                test_id=test_id,
                state=first.state,
                start_ns=first.timestamp_ns,
                end_ns=end,
                run_count=index - start_index,
            )
        )
        start_index = index

    transitions = tuple(
        BitTransition(
            component=component,
            test_id=test_id,
            timestamp_ns=later.start_ns,
            previous=earlier.state,
            current=later.state,
        )
        for earlier, later in zip(intervals, intervals[1:])
    )
    return BitTrend(
        component=component,
        test_id=test_id,
        intervals=tuple(intervals),
        transitions=transitions,
    )


def build_trends(
    results: Iterable[BitResult],
    *,
    end_ns: int | None = None,
) -> tuple[BitTrend, ...]:
    """Karışık bir BIT sonucu dizisini bileşen başına trendlere ayırır.

    Sonuç, ilk görülme sırasıyla döner; böylece listede kararlı bir sıra
    oluşur.
    """
    grouped: dict[tuple[int, str], list[BitResult]] = {}
    for item in results:
        grouped.setdefault((item.test_id, item.component), []).append(item)
    return tuple(build_trend(group, end_ns=end_ns) for group in grouped.values())
