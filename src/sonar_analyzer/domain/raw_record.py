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


@dataclass(frozen=True)
class SampleInspection:
    """Tek bir örneğin geliştirici görünümü — `F3-040`.

    `byte_offset`: örneği taşıyan kaydın dosyadaki başlangıcı.
    `raw_value`: kayıtta saklanan ham değer (gain/offset uygulanmadan).
    `scaled_value`: `raw_value * gain + offset` — fiziksel değer.
    """

    channel_id: str
    timestamp_ns: int
    byte_offset: int
    raw_value: float
    scaled_value: float
