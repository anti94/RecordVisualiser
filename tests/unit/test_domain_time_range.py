"""TimeRange ve RecordingMetadata testleri — `F1-013`."""

from __future__ import annotations

import pytest

from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange

SECOND = 1_000_000_000


def test_reversed_range_is_rejected() -> None:
    with pytest.raises(ValueError, match="Ters zaman araligi"):
        TimeRange(start_ns=5 * SECOND, end_ns=1 * SECOND)


def test_zero_length_range_is_valid_but_empty() -> None:
    empty = TimeRange(SECOND, SECOND)
    assert empty.is_empty
    assert empty.duration_ns == 0


def test_duration_and_seconds() -> None:
    span = TimeRange(0, 2 * SECOND)
    assert span.duration_ns == 2 * SECOND
    assert span.duration_seconds == 2.0


def test_contains_excludes_end() -> None:
    span = TimeRange(0, SECOND)
    assert span.contains(0)
    assert span.contains(SECOND - 1)
    assert not span.contains(SECOND), "bitis sinirina dahil degildir"
    assert not span.contains(-1)


def test_overlaps() -> None:
    first = TimeRange(0, 2 * SECOND)
    assert first.overlaps(TimeRange(SECOND, 3 * SECOND))
    assert not first.overlaps(TimeRange(2 * SECOND, 3 * SECOND)), "bitisik araliklar kesismez"
    assert not first.overlaps(TimeRange(5 * SECOND, 6 * SECOND))


def test_intersection() -> None:
    first = TimeRange(0, 3 * SECOND)
    other = TimeRange(SECOND, 5 * SECOND)
    assert first.intersection(other) == TimeRange(SECOND, 3 * SECOND)
    assert first.intersection(TimeRange(9 * SECOND, 10 * SECOND)) is None


def test_clamp_keeps_result_inside_bounds() -> None:
    bounds = TimeRange(SECOND, 4 * SECOND)
    assert TimeRange(0, 10 * SECOND).clamp(bounds) == bounds
    assert TimeRange(0, 2 * SECOND).clamp(bounds) == TimeRange(SECOND, 2 * SECOND)
    # Tamamen disarida kalan aralik sinira yapisir ve bos olur.
    assert TimeRange(0, SECOND // 2).clamp(bounds).is_empty


def test_shift_and_from_seconds() -> None:
    assert TimeRange(0, SECOND).shifted(SECOND) == TimeRange(SECOND, 2 * SECOND)
    assert TimeRange.from_seconds(0.125, 0.25) == TimeRange(125_000_000, 250_000_000)


def test_of_duration_rejects_negative() -> None:
    assert TimeRange.of_duration(0, SECOND) == TimeRange(0, SECOND)
    with pytest.raises(ValueError, match="Sure negatif"):
        TimeRange.of_duration(0, -1)


def test_record_count_uses_125ms_grid() -> None:
    assert TimeRange(0, SECOND).record_count == 8
    assert TimeRange(0, RECORD_PERIOD_NS).record_count == 1
    assert TimeRange(0, RECORD_PERIOD_NS - 1).record_count == 0


def make_recording(**overrides: object) -> RecordingMetadata:
    defaults: dict[str, object] = {
        "recording_id": "rec-001",
        "source_path": "D:/kayitlar/ornek.bin",
        "time_range": TimeRange(0, SECOND),
        "channel_count": 8,
        "record_count": 8,
    }
    defaults.update(overrides)
    return RecordingMetadata(**defaults)  # type: ignore[arg-type]


def test_recording_carries_start_and_end() -> None:
    recording = make_recording()
    assert recording.start_ns == 0
    assert recording.end_ns == SECOND
    assert recording.duration_seconds == 1.0
    assert recording.channel_count == 8


def test_recording_detects_missing_records() -> None:
    tam = make_recording(record_count=8)
    assert tam.expected_record_count == 8
    assert tam.missing_record_count == 0
    assert not tam.has_gaps

    eksik = make_recording(record_count=7)
    assert eksik.missing_record_count == 1
    assert eksik.has_gaps


def test_recording_record_rate() -> None:
    assert make_recording().sample_rate_hz == 8.0


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"recording_id": " "}, "kimligi bos"),
        ({"source_path": ""}, "yolu bos"),
        ({"channel_count": -1}, "kanal sayisi negatif"),
        ({"record_count": -1}, "kayit sayisi negatif"),
        ({"record_period_ns": 0}, "periyodu pozitif"),
        ({"file_size_bytes": -5}, "dosya boyutu negatif"),
    ],
)
def test_recording_rejects_invalid_values(overrides: dict[str, object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        make_recording(**overrides)
