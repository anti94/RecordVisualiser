"""Profil B akustik sorgu girişleri — F4-013, F4-092.

Tek sorgu yardımcıları indeksi kurup pencereyi okur. Art arda sorgulayan
kaynaklar AcousticQuery oturumunu bir kez oluşturup query() kullanmalıdır.
"""

from __future__ import annotations

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.profile_b_indexed_query import AcousticQuery
from sonar_analyzer.io.profile_b_format import ACOUSTIC_SAMPLE_RATE_HZ
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer


def query_acoustic_channel(
    buffer: ReadableBuffer,
    channel_id: int,
    time_range: TimeRange,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> DataChunk:
    """Yarı açık zaman penceresini okur; tam kaynak örnek dizisi oluşturmaz."""
    return AcousticQuery(buffer, sample_rate_hz).query(channel_id, time_range)


def acoustic_recording_span(
    buffer: ReadableBuffer,
    channel_id: int,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> TimeRange | None:
    """Örnek okumadan kayıt/blok indeksinden kanalın zaman aralığını bulur."""
    return AcousticQuery(buffer, sample_rate_hz).span(channel_id)
