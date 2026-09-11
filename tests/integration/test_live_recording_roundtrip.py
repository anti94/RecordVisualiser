"""Canlı kayıt dosyasını tekrar açarak karşılaştırma — `F5-035`.

Kabul: **Örnekler, olaylar ve 125 ms sınırları kaynaktaki referansla
eşleşir.**

Bu dosya kapalı bir döngüyü test eder: bilinen bir canlı akış üretilir,
`RotatingRecorder` ile `.bin` olarak yazılır, sonra **üretim dosya
deposuyla** (`FileRecordingRepository`) yeniden açılır ve geri okunan
şeyler akışın *kendisiyle* karşılaştırılır.

Referans, yazıcıdan ya da okuyucudan sorulmaz: testin canlı paketleri
kurarken kullandığı değerlerdir. Aksi hâlde test yalnız "yazdığımı
okudum" derdi; burada sorulan soru "kaynaktaki veriyi okudum mu".
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import BitResult, BitState, Severity
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval, TxState
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.recording.accumulator import LossyRecordError, RecordAccumulator
from sonar_analyzer.recording.rotation import RotatingRecorder, RotationPolicy
from sonar_analyzer.recording.session import RecordingSession
from sonar_analyzer.repository.file_repository import FileRecordingRepository

#: Izgaraya oturan bir baslangic (tam saniye), 2026-09-11T21:00:00Z civari.
START_NS = 1_788_901_200_000_000_000
CHANNEL_IDS = [f"ch{index}" for index in range(8)]
CHANNELS = tuple(
    ChannelMetadata(id=channel_id, path=f"/{channel_id}", name=channel_id, dtype="float32")
    for channel_id in CHANNEL_IDS
)


def _at(window: int) -> int:
    return START_NS + window * RECORD_PERIOD_NS


def _reference_value(window: int, channel_index: int) -> float:
    """Kaynak referansı: tam olarak temsil edilebilen (2'nin kuvveti) değerler.

    float32'ye yuvarlama kaybı olmasın diye seçildi; testin ölçtüğü şey
    yuvarlama değil, verinin korunması.
    """
    return float(window) + channel_index / 8.0


def _packet(
    window: int,
    *,
    bit_results: list[BitResult] | None = None,
    transmissions: list[TransmissionInterval] | None = None,
) -> LivePacket:
    chunks = [
        DataChunk(
            channel_id,
            np.array([_at(window)], dtype=np.int64),
            np.array([_reference_value(window, index)], dtype=np.float64),
        )
        for index, channel_id in enumerate(CHANNEL_IDS)
    ]
    return LivePacket(
        sequence_no=window,
        received_ns=_at(window),
        chunks=chunks,
        bit_results=list(bit_results or []),
        transmissions=list(transmissions or []),
    )


def _bit(window: int, component: str, state: BitState) -> BitResult:
    return BitResult(
        timestamp_ns=_at(window),
        test_id=1,
        component=component,
        state=state,
        severity=Severity.ERROR if state.is_failure else Severity.INFO,
    )


def _record(tmp_path: Path, packets: list[LivePacket]) -> Path:
    """Paketleri gerçekten diske yazar ve tek dosyanın yolunu döner."""

    def session_factory(path: Path) -> RecordingSession:
        return RecordingSession(path, free_space=lambda _p: 1 << 40)

    recorder = RotatingRecorder(
        tmp_path,
        "Data",
        CHANNEL_IDS,
        policy=RotationPolicy(max_bytes=1 << 30),
        session_factory=session_factory,
    )
    for packet in packets:
        recorder.accept(packet)
    outcomes = recorder.stop()
    assert all(outcome.succeeded for outcome in outcomes)
    assert len(recorder.paths) == 1
    return recorder.paths[0]


def _reopen(path: Path, tmp_path: Path) -> FileRecordingRepository:
    repository = FileRecordingRepository()
    repository.open(path, cache_path=tmp_path / "index.sidx")
    return repository


# --------------------------------------------------------------------------- #
# ORNEKLER kaynaktaki referansla eslesir
# --------------------------------------------------------------------------- #


def test_every_sample_survives_the_round_trip(tmp_path: Path) -> None:
    """Her kanalın her örneği, kaynakta ne ise dosyada o."""
    packets = [_packet(window) for window in range(24)]
    repository = _reopen(_record(tmp_path, packets), tmp_path)
    span = repository.metadata().time_range

    for index, channel_id in enumerate(CHANNEL_IDS):
        chunk = repository.query(channel_id, span)
        expected = [_reference_value(window, index) for window in range(24)]
        assert list(chunk.values) == expected, f"{channel_id} degerleri kaynakla eslesmedi"


def test_the_sample_timestamps_match_the_source(tmp_path: Path) -> None:
    packets = [_packet(window) for window in range(16)]
    repository = _reopen(_record(tmp_path, packets), tmp_path)
    span = repository.metadata().time_range

    chunk = repository.query("ch0", span)
    assert list(chunk.timestamps_ns) == [_at(window) for window in range(16)]


def test_the_channel_count_and_order_are_preserved(tmp_path: Path) -> None:
    repository = _reopen(_record(tmp_path, [_packet(0), _packet(1)]), tmp_path)
    assert len(repository.channels()) == len(CHANNEL_IDS)


# --------------------------------------------------------------------------- #
# 125 ms SINIRLARI kaynaktaki referansla eslesir
# --------------------------------------------------------------------------- #


def test_the_record_period_is_125_ms_in_the_reopened_file(tmp_path: Path) -> None:
    repository = _reopen(_record(tmp_path, [_packet(w) for w in range(8)]), tmp_path)
    assert repository.metadata().record_period_ns == RECORD_PERIOD_NS == 125_000_000


def test_consecutive_samples_are_exactly_125_ms_apart(tmp_path: Path) -> None:
    """Izgara kaymaz: ardışık örnekler arasındaki fark tam 125 ms."""
    repository = _reopen(_record(tmp_path, [_packet(w) for w in range(20)]), tmp_path)
    span = repository.metadata().time_range
    stamps = list(repository.query("ch0", span).timestamps_ns)

    deltas = {int(b - a) for a, b in zip(stamps, stamps[1:])}
    assert deltas == {RECORD_PERIOD_NS}


def test_the_first_sample_lands_on_the_recording_start(tmp_path: Path) -> None:
    repository = _reopen(_record(tmp_path, [_packet(w) for w in range(6)]), tmp_path)
    span = repository.metadata().time_range
    assert span.start_ns == _at(0)


def test_a_gap_keeps_the_remaining_samples_on_the_grid(tmp_path: Path) -> None:
    """Kayıp pencereler boşluk bırakır; kalanlar kendi ızgara noktalarında durur."""
    windows = [0, 1, 2, 7, 8, 12]
    repository = _reopen(_record(tmp_path, [_packet(w) for w in windows]), tmp_path)
    span = repository.metadata().time_range

    stamps = list(repository.query("ch0", span).timestamps_ns)
    assert stamps == [_at(window) for window in windows]


def test_the_values_after_a_gap_still_match_their_own_window(tmp_path: Path) -> None:
    windows = [0, 5, 11]
    repository = _reopen(_record(tmp_path, [_packet(w) for w in windows]), tmp_path)
    span = repository.metadata().time_range

    chunk = repository.query("ch3", span)
    assert list(chunk.values) == [_reference_value(window, 3) for window in windows]


# --------------------------------------------------------------------------- #
# OLAYLAR kaynaktaki referansla eslesir
# --------------------------------------------------------------------------- #


def test_a_bit_failure_survives_the_round_trip(tmp_path: Path) -> None:
    """Kaynakta arızalanan bileşen, dosyadan da arızalı okunur."""
    packets = [_packet(window) for window in range(4)]
    packets.append(_packet(4, bit_results=[_bit(4, "Power Supply", BitState.FAIL)]))
    packets += [_packet(window) for window in range(5, 8)]
    repository = _reopen(_record(tmp_path, packets), tmp_path)
    span = repository.metadata().time_range

    failures = [result for result in repository.bit_results(span) if result.is_failure]
    assert failures, "kaynaktaki ariza dosyada bulunamadi"
    assert {result.component for result in failures} == {"Power Supply"}


def test_the_bit_failure_is_at_the_window_it_happened(tmp_path: Path) -> None:
    packets = [_packet(window) for window in range(4)]
    packets.append(_packet(4, bit_results=[_bit(4, "Communication", BitState.FAIL)]))
    packets += [_packet(window) for window in range(5, 8)]
    repository = _reopen(_record(tmp_path, packets), tmp_path)
    span = repository.metadata().time_range

    failures = [result for result in repository.bit_results(span) if result.is_failure]
    assert {result.timestamp_ns for result in failures} == {_at(4)}


def test_a_healthy_run_reports_no_bit_failure(tmp_path: Path) -> None:
    """Kaynakta arıza yoksa dosyada da yok — uydurma arıza üretilmez."""
    repository = _reopen(_record(tmp_path, [_packet(w) for w in range(10)]), tmp_path)
    span = repository.metadata().time_range

    assert [result for result in repository.bit_results(span) if result.is_failure] == []


def test_a_transmission_interval_survives_the_round_trip(tmp_path: Path) -> None:
    """Kaynaktaki TX aralığı, dosyadan aynı sınırlarla geri gelir."""
    active = TransmissionInterval(time_range=TimeRange(_at(3), _at(6)), state=TxState.ACTIVE)
    packets = [
        _packet(window, transmissions=[active] if 3 <= window < 6 else []) for window in range(10)
    ]
    repository = _reopen(_record(tmp_path, packets), tmp_path)
    span = repository.metadata().time_range

    intervals = repository.transmissions(span)
    assert len(intervals) == 1
    assert intervals[0].start_ns == _at(3)  # ilk ACTIVE ornek
    # Kayitta `tx_status` bir ORNEKTIR: ACTIVE son olarak 5. pencerede
    # goruldu, 6. pencerede IDLE'di. Aralik bu yuzden 6'da kapanir —
    # gercek bitis ikisinin arasindadir ve bu belirsizlik 125 ms'dir.
    assert intervals[0].end_ns == _at(6)
    assert intervals[0].boundary_uncertainty_ns == RECORD_PERIOD_NS


def test_a_run_without_transmissions_reports_none(tmp_path: Path) -> None:
    repository = _reopen(_record(tmp_path, [_packet(w) for w in range(8)]), tmp_path)
    span = repository.metadata().time_range
    assert list(repository.transmissions(span)) == []


# --------------------------------------------------------------------------- #
# tasinamayan veri SESSIZCE KIRPILMAZ
# --------------------------------------------------------------------------- #


def test_an_unmappable_component_is_refused_rather_than_dropped() -> None:
    """Profil A tablosunda olmayan bileşenin arızası sessizce yutulmaz."""
    accumulator = RecordAccumulator(START_NS, CHANNEL_IDS)
    packet = _packet(0, bit_results=[_bit(0, "Kuantum Isinlayici", BitState.FAIL)])

    with pytest.raises(LossyRecordError, match="bit_status tablosunda yok"):
        accumulator.accept(packet)


def test_a_passing_component_does_not_set_any_bit() -> None:
    """Sadece arıza bit açar; geçen test maskeyi kirletmez."""
    accumulator = RecordAccumulator(START_NS, CHANNEL_IDS)
    record = accumulator.accept(_packet(0, bit_results=[_bit(0, "Power Supply", BitState.PASS)]))

    assert record is not None
    from sonar_analyzer.io.readers.binary_reader import read_data_record_v1

    assert read_data_record_v1(record.payload, 0).bit_status == 0
