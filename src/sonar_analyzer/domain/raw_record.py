"""Geliştirici Inspector'ına sunulan ham kayıt ayrıntısı — F2-037."""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.domain.data_chunk import Quality


@dataclass(frozen=True)
class RawRecordInspection:
    recording_id: str
    source_path: str
    byte_offset: int
    raw_bytes: bytes
    timestamp_ns: int | None
    fields: tuple[tuple[str, str], ...]
    quality: Quality = Quality.OK
