"""125 ms kayıt biriktirme sınırları — `F5-027`.

Kabul: **`Data00000` ve `Data00001` 125 ms aralıklarla oluşur; ham blok
örnekleri korunur.**

İkinci yarı bir **sınır** olarak test edilir: Profil A kaydı kanal başına
tek değer taşır, bir pencerede daha fazlası gelirse accumulator sessizce
kırpmaz — reddeder. Sessiz kırpma, kullanıcının veri kaybettiğini hiç
bilmemesi demek olurdu.
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.io.readers.binary_reader import read_data_record_v1
from sonar_analyzer.recording.accumulator import (
    RECORD_PERIOD_US,
    LossyRecordError,
    RecordAccumulator,
)

START_NS = 1_788_901_200_000_000_000
CHANNELS = [f"ch{index}" for index in range(8)]


def _accumulator(**kwargs: object) -> RecordAccumulator:
    return RecordAccumulator(START_NS, CHANNELS, **kwargs)  # type: ignore[arg-type]


def _packet(window: int, *, values: dict[str, float] | None = None) -> LivePacket:
    """`window`. 125 ms penceresinde kanal başına tek örnek taşıyan paket."""
    at_ns = START_NS + window * RECORD_PERIOD_NS
    payload = values if values is not None else {channel: float(window) for channel in CHANNELS}
    chunks = [
        DataChunk(
            channel_id,
            np.array([at_ns], dtype=np.int64),
            np.array([value], dtype=np.float64),
        )
        for channel_id, value in payload.items()
    ]
    return LivePacket(sequence_no=window, received_ns=at_ns, chunks=chunks)


# --------------------------------------------------------------------------- #
# Data00000 ve Data00001 125 ms araliklarla olusur
# --------------------------------------------------------------------------- #


def test_the_first_two_records_are_125_ms_apart() -> None:
    accumulator = _accumulator()
    first = accumulator.accept(_packet(0))
    second = accumulator.accept(_packet(1))

    assert first is not None and second is not None
    assert first.name == "Data00000"
    assert second.name == "Data00001"
    assert second.elapsed_us - first.elapsed_us == RECORD_PERIOD_US == 125_000


def test_the_sequence_comes_from_time_not_from_a_counter() -> None:
    """Bir pencere hiç gelmezse sonraki kayıt **kendi** sırasına oturur."""
    accumulator = _accumulator()
    accumulator.accept(_packet(0))
    skipped = accumulator.accept(_packet(3))  # 1 ve 2 hic gelmedi

    assert skipped is not None
    assert skipped.name == "Data00003"  # sayac 1 demezdi, zaman 3 diyor
    assert skipped.elapsed_us == 3 * RECORD_PERIOD_US


def test_a_long_run_keeps_the_125_ms_grid() -> None:
    accumulator = _accumulator()
    records = [accumulator.accept(_packet(index)) for index in range(16)]

    assert all(record is not None for record in records)
    elapsed = [record.elapsed_us for record in records if record is not None]
    assert elapsed == [index * 125_000 for index in range(16)]


def test_samples_inside_the_window_land_in_the_same_record() -> None:
    """Pencerenin herhangi bir anındaki örnek o pencerenin kaydına düşer."""
    accumulator = _accumulator()
    for offset_ns in (0, RECORD_PERIOD_NS // 2, RECORD_PERIOD_NS - 1):
        assert accumulator.sequence_for(START_NS + offset_ns) == 0
    assert accumulator.sequence_for(START_NS + RECORD_PERIOD_NS) == 1


def test_a_time_before_the_recording_start_is_refused() -> None:
    accumulator = _accumulator()
    with pytest.raises(ValueError, match="Zaman kayit baslangicindan once"):
        accumulator.sequence_for(START_NS - 1)


# --------------------------------------------------------------------------- #
# HAM BLOK ORNEKLERI KORUNUR
# --------------------------------------------------------------------------- #


def test_the_written_values_survive_into_the_decoded_record() -> None:
    """Yazılan değerler üretim decoder'ından aynen geri okunur."""
    accumulator = _accumulator()
    values = {channel: float(index) * 1.5 for index, channel in enumerate(CHANNELS)}
    record = accumulator.accept(_packet(0, values=values))

    assert record is not None
    decoded = read_data_record_v1(record.payload, 0)
    assert list(decoded.sensor_values) == [values[channel] for channel in CHANNELS]


def test_the_channel_order_follows_the_declared_order() -> None:
    """Değerler kanal sırasına göre yazılır — paket sırasına göre değil."""
    accumulator = _accumulator()
    reversed_payload = {channel: float(index) for index, channel in enumerate(reversed(CHANNELS))}
    record = accumulator.accept(_packet(0, values=reversed_payload))

    assert record is not None
    decoded = read_data_record_v1(record.payload, 0)
    assert list(decoded.sensor_values) == [reversed_payload[channel] for channel in CHANNELS]


def test_more_than_one_sample_per_window_is_refused_not_truncated() -> None:
    """Profil A kanal başına tek değer tutar; fazlası **sessizce kırpılmaz**."""
    accumulator = _accumulator()
    at_ns = START_NS
    dense = DataChunk(
        "ch0",
        np.array([at_ns, at_ns + 1000], dtype=np.int64),
        np.array([1.0, 2.0], dtype=np.float64),
    )
    packet = LivePacket(sequence_no=0, received_ns=at_ns, chunks=[dense])

    with pytest.raises(LossyRecordError, match="Profil B"):
        accumulator.accept(packet)


def test_the_lossy_error_names_the_channel_and_the_sample_count() -> None:
    accumulator = _accumulator()
    dense = DataChunk(
        "ch3",
        np.array([START_NS, START_NS + 1, START_NS + 2], dtype=np.int64),
        np.array([1.0, 2.0, 3.0], dtype=np.float64),
    )
    with pytest.raises(LossyRecordError) as excinfo:
        accumulator.accept(LivePacket(0, START_NS, chunks=[dense]))

    assert "ch3" in str(excinfo.value)
    assert "3 ornek" in str(excinfo.value)


def test_a_missing_channel_is_written_as_zero_not_dropped() -> None:
    """Kayıt düzeni sabit 8 alandır; eksik kanal alanı boş bırakılamaz."""
    accumulator = _accumulator()
    record = accumulator.accept(_packet(0, values={"ch0": 5.0, "ch7": 9.0}))

    assert record is not None
    decoded = read_data_record_v1(record.payload, 0)
    assert decoded.sensor_values[0] == 5.0
    assert decoded.sensor_values[7] == 9.0
    assert decoded.sensor_values[1:7] == (0.0,) * 6


# --------------------------------------------------------------------------- #
# bos paket ve sayac
# --------------------------------------------------------------------------- #


def test_a_packet_without_samples_produces_no_record() -> None:
    accumulator = _accumulator()
    assert accumulator.accept(LivePacket(sequence_no=0, received_ns=START_NS)) is None
    assert accumulator.record_count == 0


def test_the_record_count_follows_produced_records() -> None:
    accumulator = _accumulator()
    for index in range(4):
        accumulator.accept(_packet(index))
    assert accumulator.record_count == 4


# --------------------------------------------------------------------------- #
# yapilandirma dogrulamasi
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("count", [0, 4, 7, 9])
def test_a_wrong_channel_count_is_refused(count: int) -> None:
    with pytest.raises(ValueError, match="Profil A 8 kanal bekler"):
        RecordAccumulator(START_NS, [f"ch{i}" for i in range(count)])


def test_a_negative_start_time_is_refused() -> None:
    with pytest.raises(ValueError, match="start_time_utc_ns negatif olamaz"):
        RecordAccumulator(-1, CHANNELS)


def test_the_accumulator_reports_its_configuration() -> None:
    accumulator = _accumulator()
    assert accumulator.start_time_utc_ns == START_NS
    assert accumulator.channel_ids == CHANNELS
