"""Kesik son kaydı raporlama — `F2-009`.

`docs/format/fixture-corrupt.md` K-02: canlı kayıt sırasında kesilen bir
dosya **normal karşılanır**. Önceki tam kayıtlar erişilebilir kalır; kesik
son kayıt domain modeline hiç girmez, yalnız bir uyarı olarak raporlanır
(hata değil — dosya açmayı reddetmez).
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.io.profile_a_format import EXPECTED_HEADER_SIZE_V1, EXPECTED_RECORD_SIZE_V1


@dataclass(frozen=True)
class TruncatedTail:
    """Dosya sonundaki tam olmayan kaydın konumu ve boyutu."""

    byte_offset: int
    available_bytes: int
    required_bytes: int

    def __str__(self) -> str:
        return (
            f"Kesik kayit: offset {self.byte_offset}, "
            f"{self.available_bytes}/{self.required_bytes} byte"
        )


def find_truncated_tail(
    buffer_length: int,
    header_size: int = EXPECTED_HEADER_SIZE_V1,
    record_size: int = EXPECTED_RECORD_SIZE_V1,
) -> TruncatedTail | None:
    """Dosya sonunda tam olmayan bir kayıt varsa raporlar; yoksa `None`.

    Bu bir **hata değil, uyarıdır**: dosya açmayı reddetmez (K-02).
    """
    if buffer_length < header_size:
        return None  # kesik header ayri bir durum (F2-004)

    body_length = buffer_length - header_size
    remainder = body_length % record_size
    if remainder == 0:
        return None

    full_records = body_length // record_size
    return TruncatedTail(
        byte_offset=header_size + full_records * record_size,
        available_bytes=remainder,
        required_bytes=record_size,
    )
