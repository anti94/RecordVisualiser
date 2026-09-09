"""Sıra ve zaman boşluklarını raporlama — `F2-008`.

`docs/format/timing-and-naming.md` §4: kayıp periyot için kayıt yazılmaz;
tespit ardışık iki kayıt arasındaki `sequence_no` farkına bakar. Bu modül
yalnız **ileri** boşlukları (delta > 1) raporlar; geri giden `sequence_no`
boşluk değildir, ayrı bir teşhistir (`F2-011`).

**Sonraki kaydın zamanı kaydırılmaz:** boşluk raporlanır ama kayıtların
kendi `elapsed_us`/`sequence_no` alanlarına dokunulmaz — bu yüzden
`record_timestamp_ns` çağrıları öncesi/sonrası aynı sonucu verir.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from sonar_analyzer.io.profile_a_format import EXPECTED_PERIOD_US, DataRecordV1


@dataclass(frozen=True)
class SequenceGap:
    """İki ardışık kayıt arasındaki kayıp periyot(lar)."""

    before_sequence_no: int
    after_sequence_no: int
    missing_count: int
    gap_us: int

    @property
    def first_missing_sequence_no(self) -> int:
        return self.before_sequence_no + 1

    @property
    def last_missing_sequence_no(self) -> int:
        return self.after_sequence_no - 1


def detect_gaps(
    records: Iterable[DataRecordV1],
    period_us: int = EXPECTED_PERIOD_US,
) -> Iterator[SequenceGap]:
    """Ardışık kayıtlar arasındaki ileri boşlukları bulur.

    `docs/format/timing-and-naming.md` §4.1'deki algoritmanın birebir
    uygulamasıdır: `delta = sequence_no - prev.sequence_no`, `delta > 1`
    ise `missing = delta - 1` periyot kayıp.
    """
    previous: DataRecordV1 | None = None
    for record in records:
        if previous is not None:
            delta = record.sequence_no - previous.sequence_no
            if delta > 1:
                missing = delta - 1
                yield SequenceGap(
                    before_sequence_no=previous.sequence_no,
                    after_sequence_no=record.sequence_no,
                    missing_count=missing,
                    gap_us=missing * period_us,
                )
        previous = record
