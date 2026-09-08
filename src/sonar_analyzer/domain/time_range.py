"""Zaman aralığı — `F1-013`.

Birim kanoniktir: `int64` UTC nanosaniye (`docs/adr/ADR-003-time-base.md`).
Ters aralık (`end < start`) **kurucuda reddedilir**; sessizce düzeltilseydi,
kullanıcının yanlış girdiği aralık doğruymuş gibi sonuç üretirdi.
"""

from __future__ import annotations

from dataclasses import dataclass

NS_PER_SECOND = 1_000_000_000
NS_PER_MS = 1_000_000

#: Kayit periyodu (docs/format/timing-and-naming.md).
RECORD_PERIOD_NS = 125_000_000


@dataclass(frozen=True, order=True)
class TimeRange:
    """Kapalı-açık aralık: `[start_ns, end_ns)`."""

    start_ns: int
    end_ns: int

    def __post_init__(self) -> None:
        if self.end_ns < self.start_ns:
            raise ValueError(
                f"Ters zaman araligi: bitis ({self.end_ns}) baslangictan "
                f"({self.start_ns}) kucuk olamaz"
            )

    @property
    def duration_ns(self) -> int:
        return self.end_ns - self.start_ns

    @property
    def duration_seconds(self) -> float:
        return self.duration_ns / NS_PER_SECOND

    @property
    def is_empty(self) -> bool:
        """Başlangıç ve bitiş aynıysa aralık boştur ama geçerlidir."""
        return self.start_ns == self.end_ns

    def contains(self, timestamp_ns: int) -> bool:
        """Zaman damgası aralıkta mı? Bitiş **dahil değildir**."""
        return self.start_ns <= timestamp_ns < self.end_ns

    def overlaps(self, other: TimeRange) -> bool:
        return self.start_ns < other.end_ns and other.start_ns < self.end_ns

    def intersection(self, other: TimeRange) -> TimeRange | None:
        """Kesişim; kesişmiyorlarsa `None`."""
        start = max(self.start_ns, other.start_ns)
        end = min(self.end_ns, other.end_ns)
        if end < start:
            return None
        return TimeRange(start, end)

    def clamp(self, other: TimeRange) -> TimeRange:
        """Bu aralığı `other` sınırlarına sıkıştırır."""
        start = min(max(self.start_ns, other.start_ns), other.end_ns)
        end = max(min(self.end_ns, other.end_ns), other.start_ns)
        return TimeRange(start, end)

    def shifted(self, delta_ns: int) -> TimeRange:
        return TimeRange(self.start_ns + delta_ns, self.end_ns + delta_ns)

    @property
    def record_count(self) -> int:
        """Aralığa düşen nominal 125 ms kayıt sayısı."""
        return self.duration_ns // RECORD_PERIOD_NS

    @classmethod
    def from_seconds(cls, start_s: float, end_s: float) -> TimeRange:
        return cls(round(start_s * NS_PER_SECOND), round(end_s * NS_PER_SECOND))

    @classmethod
    def of_duration(cls, start_ns: int, duration_ns: int) -> TimeRange:
        if duration_ns < 0:
            raise ValueError(f"Sure negatif olamaz: {duration_ns}")
        return cls(start_ns, start_ns + duration_ns)

    def __str__(self) -> str:
        return f"[{self.start_ns} .. {self.end_ns}) = {self.duration_seconds:.6f} s"
