"""Sahte (simülasyon) kanal repository'si — `F1-020`.

Gerçek `.bin` kaydı gelene kadar (`docs/format/inventory.md` D-01) arayüz bu
kaynakla beslenir. Kanal sözlüğü `docs/format/channel-map.md` §2'deki sekiz
kanallı minimal sözlüktür.

**Bu veri simülasyondur.** `metadata().recording_id` ve `source_path` bunu açıkça
söyler; arayüz veri kaynağını `Simülasyon` olarak gösterir (plan Bölüm 3.1).
Sahte veri hiçbir yerde gerçek kayıt gibi sunulmaz.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import BitResult, Event
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval
from sonar_analyzer.processing.signals import NS_PER_SECOND, noise, sine
from sonar_analyzer.repository.protocol import EventFilter

#: Simulasyon kaynaginin adi; arayuzde bu metin gosterilir.
SIMULATION_LABEL = "Simülasyon"

#: Profil A minimal sozluk: kayit basina kanal basina tek deger -> 8 Hz.
DEFAULT_SAMPLE_RATE_HZ = NS_PER_SECOND / RECORD_PERIOD_NS


@dataclass(frozen=True)
class MockChannelSpec:
    """Bir sahte kanalın tanımı ve nasıl üretileceği."""

    id: str
    path: str
    name: str
    unit: str
    source: ChannelSource
    frequency_hz: float
    amplitude: float
    offset: float
    noise_amplitude: float = 0.0


#: docs/format/channel-map.md §2 ile ayni sira ve birimler.
DEFAULT_CHANNELS: tuple[MockChannelSpec, ...] = (
    MockChannelSpec(
        "ch0", "Sensors/Pressure", "Pressure", "bar", ChannelSource.SENSORS, 0.05, 20.0, 100.0
    ),
    MockChannelSpec(
        "ch1", "Sensors/Temperature", "Temperature", "C", ChannelSource.SENSORS, 0.01, 2.0, 25.0
    ),
    MockChannelSpec(
        "ch2", "Sensors/Accelerometer/X", "Accel X", "g", ChannelSource.SENSORS, 0.5, 1.0, 0.0, 0.05
    ),
    MockChannelSpec(
        "ch3", "Sensors/Accelerometer/Y", "Accel Y", "g", ChannelSource.SENSORS, 0.7, 0.8, 0.0, 0.05
    ),
    MockChannelSpec(
        "ch4", "Sensors/Accelerometer/Z", "Accel Z", "g", ChannelSource.SENSORS, 0.3, 0.5, 1.0, 0.05
    ),
    MockChannelSpec(
        "ch5",
        "Acoustic/Hydrophone 1",
        "Hydrophone 1",
        "Pa",
        ChannelSource.ACOUSTIC,
        1.5,
        4.0,
        0.0,
        0.4,
    ),
    MockChannelSpec(
        "ch6", "Navigation/Depth", "Depth", "m", ChannelSource.NAVIGATION, 0.02, 5.0, 30.0
    ),
    MockChannelSpec(
        "ch7",
        "Vehicle / Transmission/Voltage",
        "Voltage",
        "V",
        ChannelSource.TRANSMISSION,
        0.1,
        1.5,
        48.0,
    ),
)


class MockRecordingRepository:
    """`RecordingRepository` sözleşmesini sahte veriyle karşılar."""

    def __init__(
        self,
        duration_s: float = 60.0,
        start_ns: int = 0,
        sample_rate_hz: float = DEFAULT_SAMPLE_RATE_HZ,
        specs: Sequence[MockChannelSpec] = DEFAULT_CHANNELS,
        seed: int = 0,
    ) -> None:
        if duration_s <= 0:
            raise ValueError(f"Sure pozitif olmali: {duration_s}")

        self._duration_s = duration_s
        self._start_ns = start_ns
        self._sample_rate_hz = sample_rate_hz
        self._specs = tuple(specs)
        self._seed = seed
        self._closed = False
        self._cache: dict[str, DataChunk] = {}

        self._channels = tuple(
            ChannelMetadata(
                id=spec.id,
                path=spec.path,
                name=spec.name,
                dtype="float32",
                source=spec.source,
                unit=spec.unit,
                sample_rate_hz=sample_rate_hz,
                time_base_id="simulation",
            )
            for spec in self._specs
        )

    # -- sozlesme --------------------------------------------------------

    def metadata(self) -> RecordingMetadata:
        span = TimeRange.of_duration(self._start_ns, round(self._duration_s * NS_PER_SECOND))
        return RecordingMetadata(
            recording_id=f"{SIMULATION_LABEL}-{self._seed}",
            source_path=SIMULATION_LABEL,
            time_range=span,
            format_profile="A",
            channel_count=len(self._channels),
            record_count=span.record_count,
            device_id=SIMULATION_LABEL,
        )

    def channels(self) -> Sequence[ChannelMetadata]:
        return self._channels

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        if self._closed:
            raise RuntimeError("Repository kapatildi")

        full = self._channel_data(channel_id)
        if full is None:
            raise KeyError(f"Bilinmeyen kanal: {channel_id}")

        stamps = full.timestamps_ns
        start = int(np.searchsorted(stamps, time_range.start_ns, side="left"))
        end = int(np.searchsorted(stamps, time_range.end_ns, side="left"))

        selected_times = stamps[start:end]
        selected_values = full.values[start:end]

        if max_points is not None and max_points > 0 and selected_times.size > max_points:
            stride = int(np.ceil(selected_times.size / max_points))
            selected_times = selected_times[::stride]
            selected_values = selected_values[::stride]

        return DataChunk(
            channel_id=channel_id,
            timestamps_ns=np.ascontiguousarray(selected_times),
            values=np.ascontiguousarray(selected_values),
        )

    def events(
        self,
        time_range: TimeRange,
        filters: EventFilter | None = None,
    ) -> Sequence[Event]:
        del time_range, filters
        return []

    def bit_results(self, time_range: TimeRange) -> Sequence[BitResult]:
        del time_range
        return []

    def transmissions(self, time_range: TimeRange) -> Sequence[TransmissionInterval]:
        del time_range
        return []

    def close(self) -> None:
        self._closed = True
        self._cache.clear()

    # -- ic yardimcilar --------------------------------------------------

    def _spec(self, channel_id: str) -> MockChannelSpec | None:
        return next((spec for spec in self._specs if spec.id == channel_id), None)

    def _channel_data(self, channel_id: str) -> DataChunk | None:
        cached = self._cache.get(channel_id)
        if cached is not None:
            return cached

        spec = self._spec(channel_id)
        if spec is None:
            return None

        chunk = sine(
            channel_id=spec.id,
            sample_rate_hz=self._sample_rate_hz,
            duration_s=self._duration_s,
            frequency_hz=spec.frequency_hz,
            amplitude=spec.amplitude,
            offset=spec.offset,
            start_ns=self._start_ns,
        )

        if spec.noise_amplitude > 0:
            # Kanal indisi seed'e karistirilir: her kanal farkli ama
            # yeniden uretilebilir bir gurultu alir.
            channel_seed = self._seed * 1000 + self._specs.index(spec)
            grain = noise(
                channel_id=spec.id,
                sample_rate_hz=self._sample_rate_hz,
                duration_s=self._duration_s,
                amplitude=spec.noise_amplitude,
                seed=channel_seed,
                start_ns=self._start_ns,
            )
            chunk = DataChunk(
                channel_id=spec.id,
                timestamps_ns=chunk.timestamps_ns,
                values=(chunk.values + grain.values).astype(np.float32),
            )

        self._cache[channel_id] = chunk
        return chunk
