"""Transmisyon aralığı — `F1-015`.

Kayıtta transmisyon **durum örnekleri** bulunur; aralık bu örneklerden türetilir
(`docs/format/profile-a.md` §5.2, `docs/format/fixture-valid-8records.md` §5).

Sınırlar 125 ms'lik kayıt ızgarasına oturur; bu yüzden her aralık sınırı
**±1 kayıt periyodu belirsizlik** taşır ve bu belirsizlik modelde açıkça
saklanır — kullanıcıya kesinmiş gibi gösterilmez.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange


class TxState(str, Enum):
    """Transmisyon durumu.

    Profil A üç kod kullanır (`IDLE`, `ACTIVE`, `FAULT`); Profil B ayrıca
    `ARMED` taşır. İkisi de aynı modelde temsil edilir.
    """

    IDLE = "idle"
    ARMED = "armed"
    ACTIVE = "active"
    FAULT = "fault"
    UNKNOWN = "unknown"

    @classmethod
    def from_code(cls, code: int) -> TxState:
        """Ham kodu çevirir; tanınmayan kod `UNKNOWN` olur, IDLE varsayılmaz."""
        return _TX_STATE_BY_CODE.get(code, cls.UNKNOWN)

    @property
    def is_transmitting(self) -> bool:
        return self is TxState.ACTIVE


_TX_STATE_BY_CODE = {
    0: TxState.IDLE,
    1: TxState.ACTIVE,
    2: TxState.FAULT,
    3: TxState.ARMED,
}


@dataclass(frozen=True)
class TransmissionInterval:
    """Tek bir transmisyon aralığı."""

    time_range: TimeRange
    state: TxState = TxState.ACTIVE
    frequency_hz: float | None = None
    bandwidth_hz: float | None = None
    power_w: float | None = None
    mode: str = ""
    boundary_uncertainty_ns: int = RECORD_PERIOD_NS
    closed: bool = True

    def __post_init__(self) -> None:
        if self.state is TxState.IDLE:
            raise ValueError("IDLE bir transmisyon araligi olusturmaz")
        if self.frequency_hz is not None and self.frequency_hz <= 0:
            raise ValueError(f"Frekans pozitif olmali, verilen: {self.frequency_hz}")
        if self.bandwidth_hz is not None and self.bandwidth_hz < 0:
            raise ValueError(f"Bant genisligi negatif olamaz: {self.bandwidth_hz}")
        if self.power_w is not None and self.power_w < 0:
            raise ValueError(f"Guc negatif olamaz: {self.power_w}")
        if self.boundary_uncertainty_ns < 0:
            raise ValueError("Sinir belirsizligi negatif olamaz")

    @property
    def start_ns(self) -> int:
        return self.time_range.start_ns

    @property
    def end_ns(self) -> int:
        return self.time_range.end_ns

    @property
    def duration_ns(self) -> int:
        return self.time_range.duration_ns

    @property
    def duration_seconds(self) -> float:
        return self.time_range.duration_seconds

    @property
    def is_fault(self) -> bool:
        return self.state is TxState.FAULT

    def __str__(self) -> str:
        tail = "" if self.closed else " (kayit sonunda acik kaldi)"
        return (
            f"{self.state.value} {self.duration_seconds:.3f} s "
            f"+/-{self.boundary_uncertainty_ns / 1_000_000:.0f} ms{tail}"
        )

    @staticmethod
    def from_state_samples(
        samples: Iterable[tuple[int, TxState]],
        period_ns: int = RECORD_PERIOD_NS,
    ) -> list[TransmissionInterval]:
        """Ardışık durum örneklerinden aralıkları türetir.

        Kural: `ACTIVE` olmayan bir durumdan `ACTIVE`'e geçiş START,
        `ACTIVE`'ten çıkış STOP sayılır. Kayıt `ACTIVE` iken biterse aralık
        **açık** işaretlenir ve son örneğin penceresi kadar uzatılır; kapanmış
        gibi gösterilmez.
        """
        ordered: Sequence[tuple[int, TxState]] = sorted(samples, key=lambda item: item[0])
        intervals: list[TransmissionInterval] = []
        start: int | None = None

        for timestamp, state in ordered:
            if state.is_transmitting and start is None:
                start = timestamp
            elif not state.is_transmitting and start is not None:
                intervals.append(
                    TransmissionInterval(
                        time_range=TimeRange(start, timestamp),
                        boundary_uncertainty_ns=period_ns,
                    )
                )
                start = None

        if start is not None and ordered:
            last_timestamp = ordered[-1][0]
            intervals.append(
                TransmissionInterval(
                    time_range=TimeRange(start, last_timestamp + period_ns),
                    boundary_uncertainty_ns=period_ns,
                    closed=False,
                )
            )
        return intervals
