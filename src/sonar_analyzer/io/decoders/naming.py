"""Kayıt adı ve sıra numarası tutarlılığı — `F2-010`.

`docs/format/timing-and-naming.md` §2: ad yalnızca bir etikettir; sıralama,
indeksleme ve korelasyonda **daima `sequence_no`** kullanılır. Ad sarmaz —
`Data99999`'dan sonra `Data100000` gelir, sayaç sıfırlanmaz.

Bu modül adın beklenenle eşleşip eşleşmediğini denetler ama **kaydı asla
atmaz**: uyumsuzluk bir uyarıdır (`docs/format/fixture-corrupt.md` K-06),
kullanılan değer her zaman `sequence_no`'dur.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.io.profile_a_format import DataRecordV1, record_name


@dataclass(frozen=True)
class NameMismatch:
    """Kaydın `name` alanı ile `sequence_no`'dan beklenen ad arasındaki fark."""

    byte_offset: int
    found_name: str
    expected_name: str
    sequence_no: int

    def __str__(self) -> str:
        return (
            f'Ad tutarsizligi: "{self.found_name}" beklenen '
            f'"{self.expected_name}" (seq {self.sequence_no}), offset {self.byte_offset}'
        )


def check_name_consistency(record: DataRecordV1, byte_offset: int) -> NameMismatch | None:
    """Adın `sequence_no`'dan üretilen adla eşleşip eşleşmediğini denetler.

    Eşleşmezse `NameMismatch` döner (kayıt atılmaz, `sequence_no` esas
    alınır); eşleşirse `None`.
    """
    found = record.name.rstrip(b"\x00").decode("ascii", errors="replace")
    expected = record_name(record.sequence_no)
    if found == expected:
        return None
    return NameMismatch(
        byte_offset=byte_offset,
        found_name=found,
        expected_name=expected,
        sequence_no=record.sequence_no,
    )
