"""Profil B akustik bloklarını zaman sorgusuna bağlar — `F4-013`.

Bir zaman aralığı `[start_ns, end_ns)` verildiğinde o pencereye düşen
akustik örnekleri **blok ve kayıt sınırlarını aşarak** doğru biçimde
döndürür. Yarı-açık aralık: `start_ns <= t < end_ns`.

Bu iş çözümlenmiş örnek dizisi + zaman dizisi üzerinde `searchsorted`
ile dilimler; blok sınırında `profile_b_timing` tekrar üretmediği için
aralık uçları örnek atlamaz veya tekrarlamaz.

Saf NumPy — Qt yok, `GUI olmadan` doğrulanır. Tam repository entegrasyonu
`F4-053`+.
"""

from __future__ import annotations

import numpy as np

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.profile_b import channel_samples
from sonar_analyzer.io.decoders.profile_b_timing import channel_sample_times_ns
from sonar_analyzer.io.profile_b_format import ACOUSTIC_SAMPLE_RATE_HZ
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer


def query_acoustic_channel(
    buffer: ReadableBuffer,
    channel_id: int,
    time_range: TimeRange,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> DataChunk:
    """`channel_id` kanalının `time_range` penceresindeki örneklerini döndürür.

    Sonuç `DataChunk`: `timestamps_ns` kanonik `int64`, `values` `float64`
    (ham `int16`; fiziksel birim dönüşümü ayrı bir katmanın işi).
    Pencere hiçbir örneği kapsamıyorsa boş ama geçerli bir `DataChunk`
    döner (`start == end` da geçerlidir).
    """
    times = channel_sample_times_ns(buffer, channel_id, sample_rate_hz)
    samples = channel_samples(buffer, channel_id)
    if times.shape != samples.shape:
        raise ValueError(
            f"Zaman ({times.shape}) ve örnek ({samples.shape}) dizileri farklı uzunlukta"
        )

    lo = int(np.searchsorted(times, time_range.start_ns, side="left"))
    hi = int(np.searchsorted(times, time_range.end_ns, side="left"))

    return DataChunk(
        channel_id=str(channel_id),
        timestamps_ns=np.ascontiguousarray(times[lo:hi], dtype=np.int64),
        values=np.ascontiguousarray(samples[lo:hi], dtype=np.float64),
    )


def acoustic_recording_span(
    buffer: ReadableBuffer,
    channel_id: int,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> TimeRange | None:
    """Kanalın kapsadığı `[ilk_örnek, son_örnek + bir_periyot)` aralığı; boşsa `None`."""
    times = channel_sample_times_ns(buffer, channel_id, sample_rate_hz)
    if times.size == 0:
        return None
    step_ns = 1_000_000_000 // sample_rate_hz
    return TimeRange(int(times[0]), int(times[-1]) + step_ns)
