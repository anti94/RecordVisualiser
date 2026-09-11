"""İndeksi bir kez kurar; akustik sorguda yalnız örtüşen kayıtları okur — F4-092."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Generator
from dataclasses import dataclass

import numpy as np

from sonar_analyzer.analysis.downsampling import downsample_chunk
from sonar_analyzer.analysis.streaming_envelope import streaming_envelope
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

    def _selections(
        self, channel_id: int, window: TimeRange
    ) -> Generator[tuple[_BlockSpan, int, int], None, None]:
        channel = self._channels.get(channel_id)
        if channel is None or window.start_ns == window.end_ns:
            return
        first = bisect_right(channel.prefix_ends, window.start_ns)
        last = bisect_left(channel.starts, window.end_ns)
        for position in range(first, last):
            entry = channel.blocks[position]
            if entry.end_ns <= window.start_ns:
                continue
            lo = max(
                0, -(-(window.start_ns - entry.start_ns) * self.sample_rate_hz // NS_PER_SECOND)
            )
            hi = min(
                entry.block.sample_count,
                -(-(window.end_ns - entry.start_ns) * self.sample_rate_hz // NS_PER_SECOND),
            )
            if hi > lo:
                yield entry, lo, hi

    def iter_chunks(self, channel_id: int, window: TimeRange) -> Generator[DataChunk, None, None]:
        """En çok 65.536 örneklik parçalar; tüm kaydı biriktirmez.

        Her parça sıralıdır; örtüşen kayıtlar arasında zaman sırası garanti
        edilmez. Tam sorgu ve akış indirgeme bunu kendi sınırında sıralar.
        """
        self.last_records_read = 0
        for entry, lo, hi in self._selections(channel_id, window):
            self.last_records_read += 1
            valid = self._valid_crc(entry.record)
            block = entry.block
            for start in range(lo, hi, 65_536):
                stop = min(start + 65_536, hi)
                data = np.frombuffer(
                    self._buffer,
                    dtype=NUMPY_DTYPE[block.dtype_code],
                    count=stop - start,
                    offset=block.payload_offset + start * DTYPE_SIZE[block.dtype_code],
                ).astype(np.float64)
                flags = None
                if not valid:
                    data[:] = np.nan
                    flags = np.full(stop - start, int(Quality.CRC_ERROR), dtype=np.uint8)
                indices = np.arange(start, stop, dtype=np.int64)
                times = entry.start_ns + indices * NS_PER_SECOND // self.sample_rate_hz
                yield DataChunk(str(channel_id), times, data, flags)

    def query_display(
        self, channel_id: int, window: TimeRange, max_points: int
    ) -> DataChunk | None:
        """Büyük çizim penceresini akışla indirger; küçükse normal cache yolunu seçer."""
        downsample_chunk(DataChunk.empty(str(channel_id)), max_points)
        count = 0
        for _entry, lo, hi in self._selections(channel_id, window):
            count += hi - lo
            if count > max(262_144, max_points):
                return streaming_envelope(
                    self.iter_chunks(channel_id, window), str(channel_id), window, max_points
                )
        return None

    def query(self, channel_id: int, window: TimeRange) -> DataChunk:
        chunks = list(self.iter_chunks(channel_id, window))
        if not chunks:
            return DataChunk.empty(str(channel_id))
        timestamps = np.concatenate([chunk.timestamps_ns for chunk in chunks])
        result = np.concatenate([chunk.values for chunk in chunks])
        flags_array = (
            np.concatenate(
                [
                    np.zeros(len(chunk), dtype=np.uint8) if chunk.quality is None else chunk.quality
                    for chunk in chunks
                ]
            )
            if any(chunk.quality is not None for chunk in chunks)
            else None
        )
        if np.any(timestamps[1:] < timestamps[:-1]):
            order = np.argsort(timestamps, kind="stable")
            timestamps, result = timestamps[order], result[order]
            if flags_array is not None:
                flags_array = flags_array[order]
        return DataChunk(str(channel_id), timestamps, result, flags_array)
