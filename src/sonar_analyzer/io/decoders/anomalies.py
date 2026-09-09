"""Tekrarlı ve sıra dışı kayıtları raporlama — `F2-011`.

`docs/adr/ADR-003-time-base.md` §2.7:

* **Aynı zaman iki kez** — ikisi de saklanır, `duplicate` işaretlenir;
  sessizce ilki/sonuncusu seçilmez.
* **Geri giden `sequence_no`** — reset veya bozulma sayılır
  (`docs/format/timing-and-naming.md` §4.2), sıralama düzeltmesiyle
  gizlenmez.

`F2-008`'in aksine burada **ileri** boşluklar değil, tekrar ve geri gidiş
raporlanır; her ikisi de kaynak `byte_offset` ve o anki `timestamp_ns` ile
ayrılır (kabul kriteri).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Union

from sonar_analyzer.io.decoders.timing import record_timestamp_ns
from sonar_analyzer.io.profile_a_format import DataRecordV1, FileHeaderV1


@dataclass(frozen=True)
class DuplicateSequence:
    """Aynı `sequence_no` ikinci (veya sonraki) kez görüldü."""

    byte_offset: int
    sequence_no: int
    timestamp_ns: int

    def __str__(self) -> str:
        return (
            f"Tekrarli sira: seq {self.sequence_no}, "
            f"offset {self.byte_offset}, t={self.timestamp_ns}"
        )


@dataclass(frozen=True)
class OutOfOrderSequence:
    """`sequence_no` bir önceki kayıttan küçük — reset veya bozulma."""

    byte_offset: int
    sequence_no: int
    previous_sequence_no: int
    timestamp_ns: int

    def __str__(self) -> str:
        return (
            f"Sira disi kayit: seq {self.sequence_no} (onceki {self.previous_sequence_no}), "
            f"offset {self.byte_offset}, t={self.timestamp_ns}"
        )


#: `detect_anomalies`'in ürettiği iki tür.
Anomaly = Union[DuplicateSequence, OutOfOrderSequence]


def detect_anomalies(
    indexed_records: Iterable[tuple[int, DataRecordV1]],
    header: FileHeaderV1,
) -> Iterator[Anomaly]:
    """Dosyadaki fiziksel sırayla gelen `(byte_offset, record)` çiftlerini
    tarar; tekrarlı ve geri giden `sequence_no` durumlarını raporlar.

    İleri boşluklar burada raporlanmaz (`F2-008`'in konusu); bu ikisi
    birlikte kullanılarak tam bir sıra teşhisi elde edilir.
    """
    previous: DataRecordV1 | None = None
    for byte_offset, record in indexed_records:
        if previous is not None:
            delta = record.sequence_no - previous.sequence_no
            timestamp_ns = record_timestamp_ns(header, record)
            if delta == 0:
                yield DuplicateSequence(
                    byte_offset=byte_offset,
                    sequence_no=record.sequence_no,
                    timestamp_ns=timestamp_ns,
                )
            elif delta < 0:
                yield OutOfOrderSequence(
                    byte_offset=byte_offset,
                    sequence_no=record.sequence_no,
                    previous_sequence_no=previous.sequence_no,
                    timestamp_ns=timestamp_ns,
                )
        previous = record
