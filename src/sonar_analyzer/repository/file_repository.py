"""Kayıtlı dosyanın metadata ve kanal erişimi — F2-033, `F4-054`.

    BIN -> doğrulanmış header -> kayıt indeksi -> domain metadata

Kaynak salt okunur bir snapshot olarak alınır. `F4-054`: dosya artık RAM'e
kopyalanmaz, **bellek eşlemesi** (`MappedSource`, `F4-053`) üzerinden okunur.
Böylece dar bir zaman sorgusu yalnız ilgili kayıtların baytlarına dokunur;
işletim sistemi geri kalan sayfaları hiç getirmez. Repository eşlemeyi açık
tutar ve `close()` ile bırakır.
"""

from __future__ import annotations

import hashlib
import math
from bisect import bisect_left
from dataclasses import replace
from pathlib import Path
from types import TracebackType

import numpy as np

from sonar_analyzer.analysis.downsampling import envelope_indices
from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.domain.event import BitResult, Event
from sonar_analyzer.domain.raw_record import RawRecordInspection, SampleInspection
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval
from sonar_analyzer.io.decoders.channel_catalog import CHANNELS_8
from sonar_analyzer.io.decoders.crc_validation import check_record_crc
from sonar_analyzer.io.decoders.recording_events import RecordingEvents, scan_recording_events
from sonar_analyzer.io.index.cache import load_or_build_record_index
from sonar_analyzer.io.index.record_index import RecordIndexEntry, build_record_index
from sonar_analyzer.io.profile_a_format import EXPECTED_PERIOD_US, FileHeaderV1
from sonar_analyzer.io.readers.binary_reader import (
    ReadableBuffer,
    read_data_record_v1,
    read_data_record_v2,
)
from sonar_analyzer.io.readers.mapped_source import MappedSource
from sonar_analyzer.io.readers.recording_reader import MAX_TIMESTAMP_NS, read_validated_header
from sonar_analyzer.repository.protocol import EventFilter


class FileRecordingRepository:
    """Dosya açılmadan erişimi reddeder; başarılı açılış önceki snapshot'ı değiştirir."""

    def __init__(self) -> None:
        self._source: MappedSource | None = None
        self._data: ReadableBuffer | None = None
        self._header: FileHeaderV1 | None = None
        self._metadata: RecordingMetadata | None = None
        self._channels: tuple[ChannelMetadata, ...] = ()
        self._index: tuple[RecordIndexEntry, ...] = ()
        self._cache_reused = False
        self._time_index: tuple[RecordIndexEntry, ...] = ()
        self._times: tuple[int, ...] = ()
        self._event_data: RecordingEvents | None = None
        self._event_times: tuple[int, ...] = ()

    def open(self, path: Path, *, cache_path: Path | None = None) -> None:
        source = path.resolve(strict=True)
        target = (
            cache_path if cache_path is not None else source.with_suffix(source.suffix + ".sidx")
        )
        if target.resolve() == source or (target.exists() and target.samefile(source)):
            raise ValueError("Indeks hedefi kaynak kayit dosyasi olamaz")
        # F4-054: dosya kopyalanmaz; salt okunur eşleme üzerinden okunur.
        mapped = MappedSource(source)
        data = mapped.data()
        header = read_validated_header(data)
        messages: list[str] = []
        if header.version == 1:
            messages.append("Bu format CRC icermiyor; butunluk dogrulanmadi.")
        if header.period_us != EXPECTED_PERIOD_US:
            messages.append(f"Nominal 125000 us yerine {header.period_us} us kayit periyodu.")
        remaining = (len(data) - header.header_size) % header.record_size
        if remaining:
            messages.append(f"Kesik son kayit: {remaining} byte; tam kayitlar kullaniliyor.")
        try:
            cached = load_or_build_record_index(data, header, target)
            entries = cached.entries
            reused = cached.reused
        except OSError as exc:
            # Cache yazilamamasi salt okunur bir kaydin incelenmesini engellemez.
            entries = tuple(build_record_index(data, header))
            reused = False
            messages.append(f"Indeks cache kullanilamadi: {exc}")
        period_ns = header.period_us * 1000
        valid_entries = [
            entry
            for entry in entries
            if header.start_time_utc_ns <= entry.timestamp_ns <= MAX_TIMESTAMP_NS - period_ns
            and data[entry.byte_offset : entry.byte_offset + 4] == b"Data"
        ]
        if len(valid_entries) != len(entries):
            messages.append("Taninmayan veya int64 zaman sinirini asan kayitlar var.")
        valid_times = [entry.timestamp_ns for entry in valid_entries]
        end_ns = max(valid_times) + period_ns if valid_times else header.start_time_utc_ns
        recording_id = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:24]
        metadata = RecordingMetadata(
            recording_id=recording_id,
            source_path=str(source),
            time_range=TimeRange(header.start_time_utc_ns, end_ns),
            format_version=header.version,
            channel_count=header.channel_count,
            record_count=len(entries),
            record_period_ns=period_ns,
            file_size_bytes=len(data),
            diagnostics=messages,
        )
        channels = tuple(
            replace(channel, sample_rate_hz=1_000_000 / header.period_us, time_base_id=recording_id)
            for channel in CHANNELS_8
        )
        if self._source is not None:
            self._source.close()
        self._source, self._data, self._header = mapped, data, header
        self._metadata, self._channels = metadata, channels
        self._index, self._cache_reused = entries, reused
        self._time_index = tuple(sorted(valid_entries, key=lambda item: item.timestamp_ns))
        self._times = tuple(entry.timestamp_ns for entry in self._time_index)
        self._event_data = None
        self._event_times = ()

    def _require_open(self) -> tuple[ReadableBuffer, FileHeaderV1]:
        if self._data is None or self._header is None:
            raise RuntimeError("Once bir kayit dosyasi acilmali")
        return self._data, self._header

    def metadata(self) -> RecordingMetadata:
        self._require_open()
        assert self._metadata is not None
        # Domain modelindeki diagnostics listesi repository durumunu degistirmesin.
        return replace(self._metadata, diagnostics=list(self._metadata.diagnostics))

    def channels(self) -> tuple[ChannelMetadata, ...]:
        self._require_open()
        return self._channels

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        """İkili aramayla [başlangıç, bitiş) içindeki kayıtları çözer — F2-034.

        Fiziksel indeks değişmez; zaman indeksi sırasız/tekrarlı zamanları sorgu
        için kararlı sıralar. Bozuk CRC örneği NaN ve kalite bayrağıyla korunur.
        """
        data, header = self._require_open()
        slot = next(
            (i for i, channel in enumerate(self._channels) if channel.id == channel_id), None
        )
        if slot is None:
            raise KeyError(f"Bilinmeyen kanal: {channel_id}")
        if max_points is not None and max_points <= 0:
            raise ValueError("max_points pozitif olmali")
        left = bisect_left(self._times, time_range.start_ns)
        right = bisect_left(self._times, time_range.end_ns)
        selected = self._time_index[left:right]
        if not selected:
            return DataChunk.empty(channel_id)
        channel = self._channels[slot]
        values: list[float] = []
        flags: list[int] = []
        for entry in selected:
            record = read_data_record_v1(data, entry.byte_offset)
            quality = Quality.OK
            if header.version == 2:
                crc_record = read_data_record_v2(data, entry.byte_offset)
                if (
                    check_record_crc(
                        crc_record,
                        data[entry.byte_offset : entry.byte_offset + 64],
                        entry.byte_offset,
                    )
                    is not None
                ):
                    quality |= Quality.CRC_ERROR
            physical_index = (entry.byte_offset - header.header_size) // header.record_size
            if physical_index:
                previous = self._index[physical_index - 1]
                if entry.sequence_no > previous.sequence_no + 1:
                    quality |= Quality.GAP_BEFORE
                elif entry.sequence_no <= previous.sequence_no:
                    quality |= Quality.SUSPECT
            if record.elapsed_us != record.sequence_no * header.period_us:
                quality |= Quality.JITTER
            value = channel.to_physical(record.sensor_values[slot])
            if not math.isfinite(value):
                quality |= Quality.SUSPECT
                value = math.nan
            if quality & Quality.CRC_ERROR:
                value = math.nan
            values.append(value)
            flags.append(int(quality))
        keep = (
            list(range(len(values)))
            if max_points is None
            else envelope_indices(np.asarray(values, dtype=np.float64), max_points).tolist()
        )
        return DataChunk(
            channel_id=channel_id,
            timestamps_ns=np.array([selected[i].timestamp_ns for i in keep], dtype=np.int64),
            values=np.array([values[i] for i in keep], dtype=np.float32),
            quality=np.array([flags[i] for i in keep], dtype=np.uint8),
        )

    def _scan_events(self) -> RecordingEvents:
        data, header = self._require_open()
        if self._event_data is None:
            self._event_data = scan_recording_events(data, header)
            self._event_times = tuple(item.timestamp_ns for item in self._event_data.events)
        return self._event_data

    def inspect_record(self, byte_offset: int) -> RawRecordInspection:
        """Kaynak offsetteki tam kaydı ham byte ve alanlarla döndürür — F2-037."""
        data, header = self._require_open()
        if (
            byte_offset < header.header_size
            or (byte_offset - header.header_size) % header.record_size
            or byte_offset + header.record_size > len(data)
        ):
            raise ValueError(f"Tam kayit siniri olmayan offset: {byte_offset}")
        record = read_data_record_v1(data, byte_offset)
        # Ham kayıt kullanıcıya gösterilir ve kaynak kapandıktan sonra da
        # yaşar; burada eşlemeden **kopyalanır** (tek kayıt, 64 bayt).
        raw = bytes(data[byte_offset : byte_offset + header.record_size])
        quality = Quality.OK if record.name.startswith(b"Data") else Quality.SUSPECT
        timestamp = header.start_time_utc_ns + record.elapsed_us * 1000
        if timestamp > MAX_TIMESTAMP_NS - header.period_us * 1000:
            quality |= Quality.SUSPECT
        fields = [
            ("name", record.name.rstrip(bytes(1)).decode("ascii", errors="replace")),
            ("sequence_no", str(record.sequence_no)),
            ("elapsed_us", str(record.elapsed_us)),
            ("bit_status", str(record.bit_status)),
            ("tx_status", str(record.tx_status)),
        ]
        fields.extend(
            (f"CH{index}", str(value)) for index, value in enumerate(record.sensor_values)
        )
        if header.version == 2:
            crc_record = read_data_record_v2(data, byte_offset)
            fields.append(("record_crc32", f"0x{crc_record.record_crc32:08X}"))
            if check_record_crc(crc_record, raw[:64], byte_offset) is not None:
                quality |= Quality.CRC_ERROR
        metadata = self.metadata()
        return RawRecordInspection(
            metadata.recording_id,
            metadata.source_path,
            byte_offset,
            raw,
            timestamp if timestamp <= MAX_TIMESTAMP_NS - header.period_us * 1000 else None,
            tuple(fields),
            quality,
        )

    def inspect_sample(self, channel_id: str, timestamp_ns: int) -> SampleInspection:
        """`timestamp_ns`'e **en yakın** örneğin ham/ölçeklenmiş görünümü — `F3-040`.

        Kabul: seçim kaynak offsetini ve ham/ölçeklenmiş değeri gösterir.
        Kayıt yoksa `LookupError`, bilinmeyen kanal `KeyError`.
        """
        data, _header = self._require_open()
        slot = next(
            (i for i, channel in enumerate(self._channels) if channel.id == channel_id), None
        )
        if slot is None:
            raise KeyError(f"Bilinmeyen kanal: {channel_id}")
        if not self._time_index:
            raise LookupError("Kayitta ornek yok")

        pos = bisect_left(self._times, timestamp_ns)
        candidates = [i for i in (pos - 1, pos) if 0 <= i < len(self._time_index)]
        nearest = min(candidates, key=lambda i: abs(self._times[i] - timestamp_ns))
        entry = self._time_index[nearest]
        record = read_data_record_v1(data, entry.byte_offset)
        raw_value = float(record.sensor_values[slot])
        return SampleInspection(
            channel_id=channel_id,
            timestamp_ns=entry.timestamp_ns,
            byte_offset=entry.byte_offset,
            raw_value=raw_value,
            scaled_value=self._channels[slot].to_physical(raw_value),
        )

    def events(
        self, time_range: TimeRange, filters: EventFilter | None = None
    ) -> tuple[Event, ...]:
        collection = self._scan_events()
        left = bisect_left(self._event_times, time_range.start_ns)
        right = bisect_left(self._event_times, time_range.end_ns)
        return tuple(
            event
            for event in collection.events[left:right]
            if filters is None or filters.matches(event)
        )

    def bit_results(self, time_range: TimeRange) -> tuple[BitResult, ...]:
        return tuple(
            item
            for item in self._scan_events().bit_results
            if time_range.contains(item.timestamp_ns)
        )

    def transmissions(self, time_range: TimeRange) -> tuple[TransmissionInterval, ...]:
        collection = self._scan_events()
        if time_range.is_empty:
            return ()
        return tuple(
            item for item in collection.transmissions if item.time_range.overlaps(time_range)
        )

    @property
    def cache_reused(self) -> bool:
        self._require_open()
        return self._cache_reused

    def close(self) -> None:
        if self._source is not None:
            self._source.close()
        self._source = None
        self._data = None
        self._header = None
        self._metadata = None
        self._channels = ()
        self._index = ()
        self._cache_reused = False
        self._time_index = ()
        self._times = ()
        self._event_data = None
        self._event_times = ()

    def __enter__(self) -> FileRecordingRepository:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
