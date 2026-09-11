"""Kanal/olay payload kodlaması — `F5-006`.

`F5-001`'in bilinçli olarak tanımlamadığı payload biçimi: `LiveWireHeader`
çevresindeki bayt dizisinin kanal örnekleri (`DataChunk`) ve olayları
(`Event`) nasıl taşıdığı. Sabit alanlar `struct`, değişken uzunluklu
alanlar (metin, dizi) uzunluk önekiyle kodlanır — Profil B'nin
`BlockHeader`/`RecordHeader` deseniyle aynı ilke.

**Taslak.** Gerçek cihaz protokolü gelene kadar (E-01) bu kodlama
referans alınır. `values` her zaman `float64` olarak kodlanır/çözülür;
kaynağın orijinal dtype'ı (`float32` gibi) bu katmanda korunmaz — analiz
katmanı zaten `float64`'e genişletir (bkz. `sonar_analyzer.analysis`).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.io.live.wire_header import TruncatedDatagramError

_U16 = struct.Struct("<H")
_U32 = struct.Struct("<I")
_I64 = struct.Struct("<q")
_F64 = struct.Struct("<d")

#: olay opsiyonel alan bayraklari (bir bayt)
_FLAG_HAS_STATE = 1 << 0
_FLAG_VALUE_FLOAT = 1 << 1
_FLAG_VALUE_STR = 1 << 2
_FLAG_HAS_UNIT = 1 << 3


class _Writer:
    """Değişken/sabit alanları sıralı bir `bytearray`'e biriktirir."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def u8(self, value: int) -> None:
        self._buffer.append(value)

    def u16(self, value: int) -> None:
        self._buffer += _U16.pack(value)

    def u32(self, value: int) -> None:
        self._buffer += _U32.pack(value)

    def i64(self, value: int) -> None:
        self._buffer += _I64.pack(value)

    def f64(self, value: float) -> None:
        self._buffer += _F64.pack(value)

    def raw(self, data: bytes) -> None:
        self._buffer += data

    def text(self, value: str) -> None:
        """`uint16` uzunluk öneki + UTF-8 bayt."""
        encoded = value.encode("utf-8")
        self.u16(len(encoded))
        self.raw(encoded)

    def bytes_(self) -> bytes:
        return bytes(self._buffer)


@dataclass
class _Reader:
    """`_Writer`'ın tersi; kısa veri her okumada `TruncatedDatagramError`."""

    data: bytes
    offset: int = 0

    def _take(self, count: int) -> bytes:
        end = self.offset + count
        if end > len(self.data):
            raise TruncatedDatagramError(
                f"payload {self.offset} baytta {count} bayt beklerken "
                f"yalniz {len(self.data) - self.offset} bayt kaldi"
            )
        chunk = self.data[self.offset : end]
        self.offset = end
        return chunk

    def u8(self) -> int:
        return self._take(1)[0]

    def u16(self) -> int:
        return int(_U16.unpack(self._take(2))[0])

    def u32(self) -> int:
        return int(_U32.unpack(self._take(4))[0])

    def i64(self) -> int:
        return int(_I64.unpack(self._take(8))[0])

    def f64(self) -> float:
        return float(_F64.unpack(self._take(8))[0])

    def text(self) -> str:
        length = self.u16()
        return self._take(length).decode("utf-8")

    def array(self, count: int, dtype: str) -> NDArray[np.generic]:
        size = np.dtype(dtype).itemsize * count
        return np.frombuffer(self._take(size), dtype=dtype).copy()

    def at_end(self) -> bool:
        return self.offset >= len(self.data)


def encode_payload(chunks: list[DataChunk], events: list[Event]) -> bytes:
    """`(chunks, events)` çiftini tek bir payload baytına kodlar."""
    writer = _Writer()
    writer.u16(len(chunks))
    for chunk in chunks:
        writer.text(chunk.channel_id)
        writer.u8(1 if chunk.quality is not None else 0)
        writer.u32(len(chunk))
        writer.raw(chunk.timestamps_ns.astype("<i8", copy=False).tobytes())
        writer.raw(chunk.values.astype("<f8", copy=False).tobytes())
        if chunk.quality is not None:
            writer.raw(chunk.quality.astype("u1", copy=False).tobytes())

    writer.u16(len(events))
    for event in events:
        writer.i64(event.timestamp_ns)
        writer.text(event.source)
        writer.text(event.category)
        writer.text(event.severity.value)
        writer.text(event.code)
        writer.text(event.message)
        flags = 0
        if event.state is not None:
            flags |= _FLAG_HAS_STATE
        if isinstance(event.value, float):
            flags |= _FLAG_VALUE_FLOAT
        elif isinstance(event.value, str):
            flags |= _FLAG_VALUE_STR
        if event.unit is not None:
            flags |= _FLAG_HAS_UNIT
        writer.u8(flags)
        if event.state is not None:
            writer.text(event.state)
        if isinstance(event.value, float):
            writer.f64(event.value)
        elif isinstance(event.value, str):
            writer.text(event.value)
        if event.unit is not None:
            writer.text(event.unit)
    return writer.bytes_()


def decode_payload(data: bytes) -> tuple[list[DataChunk], list[Event]]:
    """`encode_payload`'ın tersi. Kısa/bozuk veri `TruncatedDatagramError`.

    Alan uzunlukları payload'tan **kısaysa** doğrudan `_Reader` bunu yakalar;
    alanlar tam uzunlukta ama içerik geçersizse (bilinmeyen `severity`, boş
    kanal kimliği gibi) domain kurucuları `ValueError` fırlatır — ikisi de
    burada tek bir `TruncatedDatagramError` altında toplanır, çağıran tek
    bir hata türünü yakalamak zorunda kalır.
    """
    try:
        return _decode_payload(data)
    except TruncatedDatagramError:
        raise
    except ValueError as exc:
        raise TruncatedDatagramError(f"payload bozuk: {exc}") from exc


def _decode_payload(data: bytes) -> tuple[list[DataChunk], list[Event]]:
    reader = _Reader(data)
    channel_count = reader.u16()
    chunks: list[DataChunk] = []
    for _ in range(channel_count):
        channel_id = reader.text()
        has_quality = reader.u8() == 1
        sample_count = reader.u32()
        timestamps = reader.array(sample_count, "<i8").astype(np.int64, copy=False)
        values = reader.array(sample_count, "<f8").astype(np.float64, copy=False)
        quality = (
            reader.array(sample_count, "u1").astype(np.uint8, copy=False) if has_quality else None
        )
        chunks.append(DataChunk(channel_id, timestamps, values, quality))

    event_count = reader.u16()
    events: list[Event] = []
    for _ in range(event_count):
        timestamp_ns = reader.i64()
        source = reader.text()
        category = reader.text()
        severity = Severity(reader.text())
        code = reader.text()
        message = reader.text()
        flags = reader.u8()
        state = reader.text() if flags & _FLAG_HAS_STATE else None
        value: float | str | None = None
        if flags & _FLAG_VALUE_FLOAT:
            value = reader.f64()
        elif flags & _FLAG_VALUE_STR:
            value = reader.text()
        unit = reader.text() if flags & _FLAG_HAS_UNIT else None
        events.append(
            Event(
                timestamp_ns=timestamp_ns,
                source=source,
                category=category,
                severity=severity,
                code=code,
                message=message,
                state=state,
                value=value,
                unit=unit,
                source_offset=None,  # canli veri dosya offseti tasimaz (F5-001)
            )
        )
    return chunks, events
