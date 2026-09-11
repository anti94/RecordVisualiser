"""İndeksi bir kez kurar; akustik sorguda yalnız örtüşen kayıtları okur — F4-092."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.crc import crc32
from sonar_analyzer.io.decoders.profile_b import ProfileBFormatError
from sonar_analyzer.io.index.profile_b_index import (
    BlockIndexEntry,
    ProfileBRecordEntry,
    build_profile_b_index,
)
from sonar_analyzer.io.profile_b_format import (
    ACOUSTIC_SAMPLE_RATE_HZ,
    BLOCK_TYPE_SENSOR_RAW,
    DTYPE_SIZE,
    END_MARKER,
    FILE_HEADER_SIZE,
    NUMPY_DTYPE,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_TRAILER,
    RECORD_TRAILER_SIZE,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer
from sonar_analyzer.repository.memory_cache import MemoryBoundedCache

NS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class _BlockSpan:
    record: ProfileBRecordEntry
    block: BlockIndexEntry
    start_ns: int
    end_ns: int


@dataclass(frozen=True)
class _ChannelSpans:
    blocks: tuple[_BlockSpan, ...]
    starts: tuple[int, ...]
    prefix_ends: tuple[int, ...]


class AcousticQuery:
    """Tek salt okunur snapshot'a bağlı, yeniden kullanılabilir sorgu oturumu.

    Kaynak/indeks ömrü çağırana aittir. Zaman indeksi örnek başına veri tutmaz.
    CRC yalnız seçilen kayıtlarda doğrulanır, sonuçları sınırlı cache'te saklanır.
    Bozuk CRC örnekleri zamanları korunarak NaN/CRC_ERROR olarak döner.
    """

    def __init__(
        self,
        buffer: ReadableBuffer,
        sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
    ) -> None:
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz pozitif olmalı")
        self._buffer = buffer
        self.sample_rate_hz = sample_rate_hz
        if len(buffer) < FILE_HEADER_SIZE:
            raise ProfileBFormatError("dosya FileHeader'dan kısa", byte_offset=0)
        expected = int.from_bytes(buffer[FILE_HEADER_SIZE - 4 : FILE_HEADER_SIZE], "little")
        if crc32(buffer[: FILE_HEADER_SIZE - 4]) != expected:
            raise ProfileBFormatError("FileHeader CRC hatası", byte_offset=FILE_HEADER_SIZE - 4)
        self.index = build_profile_b_index(buffer)
        grouped: dict[int, list[_BlockSpan]] = {}
        for record in self.index.records:
            seen: set[int] = set()
            for block in record.blocks:
                if block.block_type != BLOCK_TYPE_SENSOR_RAW or block.channel_id in seen:
                    continue
                seen.add(block.channel_id)
                if block.sample_count == 0:
                    continue
                start = self.index.header.t0_utc_ns + record.t_start_offset_ns + block.t_offset_ns
                end = start + (block.sample_count - 1) * NS_PER_SECOND // sample_rate_hz + 1
                if start < 0 or end > np.iinfo(np.int64).max:
                    raise ProfileBFormatError(
                        "örnek zamanı int64 sınırları dışında", byte_offset=block.byte_offset
                    )
                grouped.setdefault(block.channel_id, []).append(
                    _BlockSpan(record, block, start, end)
                )
        self._channels: dict[int, _ChannelSpans] = {}
        for channel, blocks in grouped.items():
            blocks.sort(key=lambda block: block.start_ns)
            high = 0
            ends: list[int] = []
            for block in blocks:
                high = max(high, block.end_ns)
                ends.append(high)
            self._channels[channel] = _ChannelSpans(
                tuple(blocks), tuple(block.start_ns for block in blocks), tuple(ends)
            )
        self._crc: MemoryBoundedCache[int, bool] = MemoryBoundedCache(
            max_bytes=4096, max_entries=4096, sizer=lambda _: 1
        )
        self.last_records_read = 0

    def span(self, channel_id: int) -> TimeRange | None:
        channel = self._channels.get(channel_id)
        if channel is None:
            return None
        return TimeRange(
            channel.starts[0], channel.prefix_ends[-1] - 1 + NS_PER_SECOND // self.sample_rate_hz
        )

    def _valid_crc(self, record: ProfileBRecordEntry) -> bool:
        cached = self._crc.get(record.byte_offset)
        if cached is not None:
            return cached
        trailer_offset = record.byte_offset + record.byte_size - RECORD_TRAILER_SIZE
        expected, marker = RECORD_TRAILER.unpack_from(self._buffer, trailer_offset)
        header_crc = RECORD_HEADER.unpack_from(self._buffer, record.byte_offset)[7]
        actual = crc32(self._buffer[record.byte_offset + RECORD_HEADER_SIZE : trailer_offset])
        valid = marker == END_MARKER and expected == header_crc == actual
        self._crc.put(record.byte_offset, valid)
        return valid

    def query(self, channel_id: int, window: TimeRange) -> DataChunk:
        self.last_records_read = 0
        channel = self._channels.get(channel_id)
        if channel is None or window.start_ns == window.end_ns:
            return DataChunk.empty(str(channel_id))
        first = bisect_right(channel.prefix_ends, window.start_ns)
        last = bisect_left(channel.starts, window.end_ns)
        values: list[NDArray[np.float64]] = []
        times: list[NDArray[np.int64]] = []
        quality: list[tuple[int, int]] = []
        touched: set[int] = set()
        for entry in channel.blocks[first:last]:
            if entry.end_ns <= window.start_ns:
                continue
            block = entry.block
            lo = max(
                0, -(-(window.start_ns - entry.start_ns) * self.sample_rate_hz // NS_PER_SECOND)
            )
            hi = min(
                block.sample_count,
                -(-(window.end_ns - entry.start_ns) * self.sample_rate_hz // NS_PER_SECOND),
            )
            if hi <= lo:
                continue
            touched.add(entry.record.byte_offset)
            data = np.frombuffer(
                self._buffer,
                dtype=NUMPY_DTYPE[block.dtype_code],
                count=hi - lo,
                offset=block.payload_offset + lo * DTYPE_SIZE[block.dtype_code],
            ).astype(np.float64)
            flags = 0
            if not self._valid_crc(entry.record):
                data[:] = np.nan
                flags = int(Quality.CRC_ERROR)
            values.append(data)
            indices = np.arange(lo, hi, dtype=np.int64)
            times.append(entry.start_ns + indices * NS_PER_SECOND // self.sample_rate_hz)
            quality.append((flags, hi - lo))
        self.last_records_read = len(touched)
        if not values:
            return DataChunk.empty(str(channel_id))
        timestamps = np.concatenate(times)
        result = np.concatenate(values)
        flags_array = (
            np.concatenate([np.full(size, flag, dtype=np.uint8) for flag, size in quality])
            if any(flag for flag, _ in quality)
            else None
        )
        if np.any(timestamps[1:] < timestamps[:-1]):
            order = np.argsort(timestamps, kind="stable")
            timestamps, result = timestamps[order], result[order]
            if flags_array is not None:
                flags_array = flags_array[order]
        return DataChunk(str(channel_id), timestamps, result, flags_array)
