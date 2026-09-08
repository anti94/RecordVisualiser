"""Olay ve BIT sonucu modelleri — `F1-014`.

Kural: **bilinmeyen kaybolmaz.** Tanınmayan bir BIT durumu `UNKNOWN` olur ve ham
kodu korunur; uydurma bir ad veya "PASS" varsayımı üretilmez
(`docs/format/channel-map.md` §4).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """Olay şiddeti; `Events` tablosunda sıralama ve renk için kullanılır."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return _SEVERITY_RANK[self]

    @classmethod
    def from_code(cls, code: int) -> Severity:
        """Sayısal şiddet kodunu çevirir; tanınmayan kod `WARNING` olur."""
        return _SEVERITY_BY_CODE.get(code, cls.WARNING)


_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
    Severity.CRITICAL: 3,
}

_SEVERITY_BY_CODE = {
    0: Severity.INFO,
    1: Severity.WARNING,
    2: Severity.ERROR,
    3: Severity.CRITICAL,
}


class BitState(str, Enum):
    """BIT testinin sonucu."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_RUN = "not_run"
    UNKNOWN = "unknown"

    @classmethod
    def from_code(cls, code: int) -> BitState:
        """Ham durum kodunu çevirir; tanınmayan kod `UNKNOWN` olur.

        `docs/format/profile-a.md` §5.2: eşleme yoksa uydurma sonuç üretilmez.
        """
        return _BIT_STATE_BY_CODE.get(code, cls.UNKNOWN)

    @property
    def is_failure(self) -> bool:
        return self in (BitState.WARN, BitState.FAIL)


_BIT_STATE_BY_CODE = {
    0: BitState.PASS,
    1: BitState.WARN,
    2: BitState.FAIL,
    3: BitState.NOT_RUN,
}


@dataclass(frozen=True)
class Event:
    """Zaman eksenine yerleşen tekil olay."""

    timestamp_ns: int
    source: str
    category: str
    severity: Severity
    code: str
    message: str
    state: str | None = None
    value: float | str | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Olay kaynagi bos olamaz")
        if not self.category.strip():
            raise ValueError(f"{self.source}: olay kategorisi bos olamaz")
        if not self.message.strip():
            raise ValueError(f"{self.source}: olay mesaji bos olamaz")

    @property
    def is_alarm(self) -> bool:
        return self.severity.rank >= Severity.ERROR.rank


@dataclass(frozen=True)
class BitResult:
    """Tek bir BIT testinin sonucu."""

    timestamp_ns: int
    test_id: int
    component: str
    state: BitState
    severity: Severity = Severity.INFO
    code: int = 0
    measured: float | None = None
    unit: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if self.test_id < 0:
            raise ValueError(f"Test kimligi negatif olamaz: {self.test_id}")
        if not self.component.strip():
            raise ValueError(f"test {self.test_id}: bilesen adi bos olamaz")

    @property
    def is_failure(self) -> bool:
        return self.state.is_failure

    @property
    def display_name(self) -> str:
        """Kullanıcıya gösterilecek ad.

        Bileşen kataloğu yoksa ham test numarası gösterilir; uydurma bir test
        adı üretilmez.
        """
        return f"{self.component} (test {self.test_id})"

    def to_event(self) -> Event:
        """BIT sonucunu ortak olay tablosunda gösterilebilir hâle çevirir."""
        value: float | str | None = self.measured
        return Event(
            timestamp_ns=self.timestamp_ns,
            source="BIT",
            category=self.component,
            severity=self.severity,
            code=str(self.code),
            message=self.detail or self.display_name,
            state=self.state.value,
            value=value,
            unit=self.unit,
        )
