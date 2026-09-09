"""Kayıtlı dosyanın metadata ve kanal erişimi — F2-033.

    BIN -> doğrulanmış header -> kayıt indeksi -> domain metadata

Kaynak salt okunur bir snapshot olarak alınır. Memory mapping/lazy payload yükleme
Faz 4 işidir; uygulama burada dosya tanıtıcısını açık tutmaz.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.channel_catalog import CHANNELS_8
from sonar_analyzer.io.index.cache import load_or_build_record_index
from sonar_analyzer.io.index.record_index import RecordIndexEntry, build_record_index
from sonar_analyzer.io.profile_a_format import EXPECTED_PERIOD_US, FileHeaderV1
from sonar_analyzer.io.readers.recording_reader import MAX_TIMESTAMP_NS, read_validated_header


class FileRecordingRepository:
    """Dosya açılmadan erişimi reddeder; başarılı açılış önceki snapshot'ı değiştirir."""

    def __init__(self) -> None:
        self._data: bytes | None = None
        self._header: FileHeaderV1 | None = None
        self._metadata: RecordingMetadata | None = None
        self._channels: tuple[ChannelMetadata, ...] = ()
        self._index: tuple[RecordIndexEntry, ...] = ()
        self._cache_reused = False

    def open(self, path: Path, *, cache_path: Path | None = None) -> None:
        source = path.resolve(strict=True)
        target = (
            cache_path if cache_path is not None else source.with_suffix(source.suffix + ".sidx")
        )
        if target.resolve() == source or (target.exists() and target.samefile(source)):
            raise ValueError("Indeks hedefi kaynak kayit dosyasi olamaz")
        data = source.read_bytes()
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
        valid_times = [
            entry.timestamp_ns
            for entry in entries
            if header.start_time_utc_ns <= entry.timestamp_ns <= MAX_TIMESTAMP_NS - period_ns
            and data[entry.byte_offset : entry.byte_offset + 4] == b"Data"
        ]
        if len(valid_times) != len(entries):
            messages.append("Taninmayan veya int64 zaman sinirini asan kayitlar var.")
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
        self._data, self._header = data, header
        self._metadata, self._channels = metadata, channels
        self._index, self._cache_reused = entries, reused

    def _require_open(self) -> tuple[bytes, FileHeaderV1]:
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

    @property
    def cache_reused(self) -> bool:
        self._require_open()
        return self._cache_reused

    def close(self) -> None:
        self._data = None
        self._header = None
        self._metadata = None
        self._channels = ()
        self._index = ()
        self._cache_reused = False
