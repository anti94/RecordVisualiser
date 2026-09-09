"""BIT maskesini durum ve değişim olaylarına çevirme — `F2-022`.

`docs/format/channel-map.md` §4/§4.1: `bit_status`'un bit 0-3'ü
Power Supply, 4-7 Communication, 8-11 Thermal Management bileşenine
karşılık gelir; bir bileşendeki bitlerden **herhangi biri** 1 ise o
bileşen `FAIL` sayılır — aynı bileşendeki birden fazla bit ayrı ayrı
değil, tek bir bileşen durumuna daralır. Bit 12-31 atanmamıştır;
atanmamış bir bit 1 olursa bileşen adı yerine ham bit numarası
kullanılır ("Bilinmeyen test (bit N)"), uydurma test adı üretilmez.

Bu modül iki şey üretir: `component_states()` bir `bit_status` değerinden
anlık bileşen durumlarını (`PASS`/`FAIL`), `detect_bit_transitions()`
ardışık kayıtlar arasında **değişen** bileşenler için olay akışı üretir —
`gaps.py`/`anomalies.py`'deki ardışık-çift karşılaştırma desenini izler.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum

from sonar_analyzer.io.profile_a_format import BIT_COMPONENT_BY_BIT, DataRecordV1

#: Bilinen bileşenler, ilk atandıkları bit sırasıyla
#: (Power Supply, Communication, Thermal Management).
_COMPONENTS_IN_BIT_ORDER: tuple[str, ...] = tuple(
    dict.fromkeys(BIT_COMPONENT_BY_BIT[bit] for bit in sorted(BIT_COMPONENT_BY_BIT))
)

#: `channel-map.md` §4.1: 12-31 atanmamıştır.
_FIRST_UNASSIGNED_BIT = 12
_LAST_BIT = 31


class BitState(str, Enum):
    """Bir bileşenin anlık durumu."""

    PASS = "pass"
    FAIL = "fail"


def component_name_for_bit(bit: int) -> str:
    """Bit numarasından bileşen adını döner; atanmamışsa ham numarayla etiket üretir."""
    return BIT_COMPONENT_BY_BIT.get(bit, f"Bilinmeyen test (bit {bit})")


def component_states(bit_status: int) -> dict[str, BitState]:
    """`bit_status`'tan, bilinen her bileşen için `PASS`/`FAIL` döner.

    Bir bileşendeki bitlerden herhangi biri 1 ise o bileşen `FAIL` olur
    (`channel-map.md` §4) — bit sayısı değil, bileşen sayısı kadar durum
    üretilir.
    """
    states: dict[str, BitState] = dict.fromkeys(_COMPONENTS_IN_BIT_ORDER, BitState.PASS)
    for bit, component in BIT_COMPONENT_BY_BIT.items():
        if bit_status & (1 << bit):
            states[component] = BitState.FAIL
    return states


def unknown_active_bits(bit_status: int) -> tuple[int, ...]:
    """12-31 arasında 1 olan (atanmamış) bitleri artan sırada döner."""
    return tuple(
        bit for bit in range(_FIRST_UNASSIGNED_BIT, _LAST_BIT + 1) if bit_status & (1 << bit)
    )


@dataclass(frozen=True)
class BitTransitionEvent:
    """Bir bileşenin durumunun ardışık iki kayıt arasında değiştiği an."""

    sequence_no: int
    byte_offset: int
    component: str
    from_state: BitState
    to_state: BitState

    def __str__(self) -> str:
        return (
            f"BIT gecisi: {self.component} {self.from_state.value} -> {self.to_state.value}, "
            f"seq {self.sequence_no}, offset {self.byte_offset}"
        )


def detect_bit_transitions(
    indexed_records: Iterable[tuple[int, DataRecordV1]],
) -> Iterator[BitTransitionEvent]:
    """Fiziksel sırayla gelen `(byte_offset, record)` çiftlerini tarar;
    ardışık kayıtlar arasında değişen BIT bileşenlerini olay olarak üretir.

    Aynı anda değişen her bileşen için **ayrı** bir olay üretilir; bir
    kayıtta hiçbir bileşen değişmemişse hiçbir olay üretilmez.
    """
    previous_states: dict[str, BitState] | None = None
    for byte_offset, record in indexed_records:
        states = component_states(record.bit_status)
        if previous_states is not None:
            for component in _COMPONENTS_IN_BIT_ORDER:
                if states[component] != previous_states[component]:
                    yield BitTransitionEvent(
                        sequence_no=record.sequence_no,
                        byte_offset=byte_offset,
                        component=component,
                        from_state=previous_states[component],
                        to_state=states[component],
                    )
        previous_states = states
