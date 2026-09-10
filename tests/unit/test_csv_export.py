"""Seçili kanal ve aralığı CSV olarak yazma — `F3-064`.

Kabul: satır sayısı, zaman, birim ve kaynak metadata doğru çıkar.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.export.csv_export import (
    DATA_COLUMNS,
    PARTIAL_SUFFIX,
    CsvExportResult,
    ExportCancelled,
    write_channel_csv,
)

NS = 1_000_000_000
#: 2023-11-14T22:13:20Z, tam saniye — ISO dönüşümü elle doğrulanabilir.
T0 = 1_700_000_000 * NS
PERIOD = NS // 8  # 8 Hz


def _channel() -> ChannelMetadata:
    return ChannelMetadata(
        id="ch0",
        path="Sensors/Pressure",
        name="Pressure",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        sample_rate_hz=8.0,
    )


def _chunk(n: int = 3) -> DataChunk:
    stamps = np.array([T0 + i * PERIOD for i in range(n)], dtype=np.int64)
    values = np.array([101.0 + 0.5 * i for i in range(n)], dtype=np.float64)
    return DataChunk(channel_id="ch0", timestamps_ns=stamps, values=values)


def _recording() -> RecordingMetadata:
    return RecordingMetadata(
        recording_id="rec-42",
        source_path="C:/data/kayit.bin",
        time_range=TimeRange(T0, T0 + 8 * PERIOD),
        channel_count=1,
        record_count=8,
        device_id="SONAR-1",
    )


def _read_lines(path: Path) -> tuple[list[str], list[list[str]]]:
    """`(# metadata satırları, csv satırları)` — önek olmadan."""
    meta: list[str] = []
    data_text: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("# "):
            meta.append(raw[2:])
        else:
            data_text.append(raw)
    rows = list(csv.reader(data_text))
    return meta, rows


def test_row_count_matches_the_sample_count(tmp_path: Path) -> None:
    result = write_channel_csv(_chunk(5), _channel(), tmp_path / "out.csv")

    assert isinstance(result, CsvExportResult)
    assert result.row_count == 5

    _meta, rows = _read_lines(result.path)
    assert rows[0] == list(DATA_COLUMNS)  # başlık
    assert len(rows) == 1 + 5  # başlık + 5 veri satırı


def test_metadata_carries_unit_source_and_recording(tmp_path: Path) -> None:
    result = write_channel_csv(
        _chunk(3),
        _channel(),
        tmp_path / "out.csv",
        recording=_recording(),
        exported_range=TimeRange(T0, T0 + 3 * PERIOD),
    )

    meta = dict(line.split("=", 1) for line in result.metadata_lines)
    assert meta["unit"] == "bar"
    assert meta["source"] == "sensors"
    assert meta["channel_name"] == "Pressure"
    assert meta["channel_path"] == "Sensors/Pressure"
    assert meta["sample_rate_hz"] == "8"
    assert meta["recording_id"] == "rec-42"
    assert meta["recording_source"] == "C:/data/kayit.bin"
    assert meta["device_id"] == "SONAR-1"
    assert meta["range_ns"] == f"[{T0},{T0 + 3 * PERIOD})"
    assert meta["row_count"] == "3"

    # dosyaya da yazıldı
    file_meta, _rows = _read_lines(result.path)
    assert "unit=bar" in file_meta
    assert "source=sensors" in file_meta


def test_time_columns_are_canonical_ns_and_utc_iso(tmp_path: Path) -> None:
    result = write_channel_csv(_chunk(3), _channel(), tmp_path / "out.csv")
    _meta, rows = _read_lines(result.path)

    body = rows[1:]  # başlığı at
    assert [r[0] for r in body] == [str(T0), str(T0 + PERIOD), str(T0 + 2 * PERIOD)]

    # UTC ISO ilk satır: tam saniye
    assert body[0][1] == datetime.fromtimestamp(T0 // NS, tz=timezone.utc).isoformat()
    # ikinci satır: 125 ms sonra
    expected = (
        datetime.fromtimestamp(T0 // NS, tz=timezone.utc).replace(microsecond=125_000).isoformat()
    )
    assert body[1][1] == expected

    # değerler korunur
    assert [float(r[2]) for r in body] == [101.0, 101.5, 102.0]


def test_metadata_can_be_omitted(tmp_path: Path) -> None:
    result = write_channel_csv(
        _chunk(2), _channel(), tmp_path / "plain.csv", include_metadata=False
    )

    assert result.metadata_lines == ()
    text = result.path.read_text(encoding="utf-8")
    assert not text.startswith("#")
    assert text.splitlines()[0] == ",".join(DATA_COLUMNS)


def test_channel_mismatch_is_rejected(tmp_path: Path) -> None:
    other = ChannelMetadata(
        id="ch9",
        path="Sensors/Other",
        name="Other",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="V",
    )
    with pytest.raises(ValueError, match="farklı"):
        write_channel_csv(_chunk(3), other, tmp_path / "x.csv")


def test_missing_parent_directories_are_created(tmp_path: Path) -> None:
    result = write_channel_csv(_chunk(1), _channel(), tmp_path / "a" / "b" / "c.csv")
    assert result.path.exists()


def test_raw_variant_inverts_the_calibration(tmp_path: Path) -> None:
    # to_physical: raw*gain + offset  ->  ters: (v - offset) / gain
    channel = ChannelMetadata(
        id="ch0",
        path="Sensors/Pressure",
        name="Pressure",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        gain=2.0,
        offset=10.0,
    )
    processed = DataChunk(
        channel_id="ch0",
        timestamps_ns=np.array([T0, T0 + PERIOD], dtype=np.int64),
        values=np.array([30.0, 50.0], dtype=np.float64),  # ham 10, 20
    )

    result = write_channel_csv(processed, channel, tmp_path / "raw.csv", raw=True)

    _meta, rows = _read_lines(result.path)
    assert [float(r[2]) for r in rows[1:]] == [10.0, 20.0]
    assert "variant=raw" in result.metadata_lines
    assert "unit=raw" in result.metadata_lines
    assert "calibration=value*2+10" in result.metadata_lines


def test_raw_variant_needs_a_non_zero_gain(tmp_path: Path) -> None:
    channel = ChannelMetadata(
        id="ch0",
        path="Sensors/Pressure",
        name="Pressure",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        gain=0.0,
    )
    with pytest.raises(ValueError, match="ters cevrilemez"):
        write_channel_csv(_chunk(2), channel, tmp_path / "x.csv", raw=True)


def test_processed_variant_is_recorded_in_metadata(tmp_path: Path) -> None:
    result = write_channel_csv(_chunk(2), _channel(), tmp_path / "p.csv")
    assert "variant=processed" in result.metadata_lines


# -- F3-066: atomik yazma + iptal --------------------------------


def _big_chunk(n: int) -> DataChunk:
    stamps = np.array([T0 + i * PERIOD for i in range(n)], dtype=np.int64)
    values = np.arange(n, dtype=np.float64)
    return DataChunk(channel_id="ch0", timestamps_ns=stamps, values=values)


def test_successful_write_leaves_no_partial_file(tmp_path: Path) -> None:
    dest = tmp_path / "ok.csv"
    write_channel_csv(_big_chunk(50), _channel(), dest)

    assert dest.exists()
    assert not dest.with_name(dest.name + PARTIAL_SUFFIX).exists()


def test_cancel_midway_raises_and_leaves_no_target(tmp_path: Path) -> None:
    dest = tmp_path / "cancelled.csv"
    written: list[int] = []

    def _cancel_after_three() -> bool:
        written.append(1)
        return len(written) > 3

    with pytest.raises(ExportCancelled):
        write_channel_csv(_big_chunk(1000), _channel(), dest, should_cancel=_cancel_after_three)

    # Kabul: yarım dosya tamamlanmış gibi sunulmaz.
    assert not dest.exists()
    assert not dest.with_name(dest.name + PARTIAL_SUFFIX).exists()


def test_cancel_does_not_touch_a_pre_existing_target(tmp_path: Path) -> None:
    dest = tmp_path / "keep.csv"
    dest.write_text("ONCEDEN VAR", encoding="utf-8")

    with pytest.raises(ExportCancelled):
        write_channel_csv(_big_chunk(500), _channel(), dest, should_cancel=lambda: True)

    assert dest.read_text(encoding="utf-8") == "ONCEDEN VAR"


def test_progress_callback_reports_written_and_total(tmp_path: Path) -> None:
    seen: list[tuple[int, int]] = []
    write_channel_csv(
        _big_chunk(10), _channel(), tmp_path / "p.csv", on_progress=lambda w, t: seen.append((w, t))
    )

    assert seen  # en az bir kez çağrıldı
    assert seen[-1] == (10, 10)  # son çağrı: tamamlandı
    assert all(0 < w <= t == 10 for w, t in seen)


def test_empty_chunk_writes_only_header_and_metadata(tmp_path: Path) -> None:
    empty = DataChunk(
        channel_id="ch0",
        timestamps_ns=np.array([], dtype=np.int64),
        values=np.array([], dtype=np.float64),
    )
    result = write_channel_csv(empty, _channel(), tmp_path / "e.csv")

    assert result.row_count == 0
    _meta, rows = _read_lines(result.path)
    assert rows == [list(DATA_COLUMNS)]
    assert "row_count=0" in result.metadata_lines
