"""Büyük dosya benchmark koşusu — `F4-064`.

Kabul: metadata, sorgu, FPS ve bellek sonuçları makine bilgisiyle üretilir.

Sayılar elle türetilebilir olsun diye küçük ama **gerçek** bir Profil B
dosyası üretilir: 80 kayıt = 10 s, kanal başına 480.000 örnek. Ölçüm
gerçek yığını (mmap + decoder + `DisplayQuery`) koşar; hiçbir aşama
taklit edilmez.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from tools.large_file_benchmark import (
    DEFAULT_VIEWPORT_SECONDS,
    TARGETS,
    benchmark_file,
    machine_info,
    measure_frame_rate,
    measure_metadata,
    measure_queries,
    peak_working_set_bytes,
    run,
    span_at,
    total_ram_bytes,
)
from tools.make_synthetic_bin import HEADER_BYTES, RECORD_BYTES, write_fixture

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.profile_b_query import query_acoustic_channel
from sonar_analyzer.io.profile_b_format import RECORD_PERIOD_NS, SAMPLES_PER_BLOCK
from sonar_analyzer.io.readers.mapped_source import MappedSource
from sonar_analyzer.repository.display_query import DisplayQuery

RECORDS = 80
#: 80 * 125 ms = 10 s.
DURATION_S = RECORDS * RECORD_PERIOD_NS / 1e9
FILE_BYTES = HEADER_BYTES + RECORDS * RECORD_BYTES


@pytest.fixture(scope="module")
def fixture_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("bench") / "profile-b.bin"
    write_fixture(target, FILE_BYTES)
    return target


@pytest.fixture(scope="module")
def span(fixture_path: Path) -> TimeRange:
    """Kaydın **gerçek** zaman aralığı; `t0` epoch sıfırı değildir."""
    with MappedSource(fixture_path) as source:
        result = measure_metadata(source.data(), verify_span=False)
    return TimeRange(result.start_ns, result.end_ns)


# --------------------------------------------------------------------------- #
# makine bilgisi
# --------------------------------------------------------------------------- #


def test_the_machine_is_identified() -> None:
    info = machine_info()
    assert set(info) == {
        "python",
        "platform",
        "processor",
        "cpu_count",
        "total_ram_bytes",
        "numpy",
    }
    assert isinstance(info["cpu_count"], int) and info["cpu_count"] >= 1
    assert info["python"].split(".")[0] == "3"  # type: ignore[union-attr]
    assert info["platform"]


def test_the_physical_memory_is_measured_or_honestly_absent() -> None:
    total = total_ram_bytes()
    # Uydurma degil: ya gercek bir olcum ya da None.
    assert total is None or total > 256 * 1024 * 1024


def test_the_peak_working_set_is_measured_or_honestly_absent() -> None:
    peak = peak_working_set_bytes()
    assert peak is None or peak > 0


# --------------------------------------------------------------------------- #
# pencere secimi
# --------------------------------------------------------------------------- #


def test_the_window_sits_at_the_requested_position() -> None:
    window = span_at(TimeRange(0, 1_000), 100)
    # 0 + int((1000 - 100) * 0.4) = 360
    assert (window.start_ns, window.end_ns) == (360, 460)


def test_a_window_wider_than_the_recording_is_clamped() -> None:
    window = span_at(TimeRange(100, 200), 10_000)
    assert (window.start_ns, window.end_ns) == (100, 200)


# --------------------------------------------------------------------------- #
# metadata
# --------------------------------------------------------------------------- #


def test_the_metadata_matches_the_generated_file(fixture_path: Path) -> None:
    with MappedSource(fixture_path) as source:
        result = measure_metadata(source.data(), verify_span=True)

    manifest = json.loads(fixture_path.with_name(fixture_path.name + ".json").read_text())
    assert result.record_count == manifest["record_count"] == RECORDS
    assert result.channel_count == 4
    assert result.channel_ids == [0, 1, 2, 3]
    assert result.record_period_ns == RECORD_PERIOD_NS
    assert result.end_ns - result.start_ns == RECORDS * RECORD_PERIOD_NS
    assert result.duration_s == DURATION_S == 10.0
    assert result.span_source == "header"
    assert result.span_verified is True
    assert result.seconds >= 0.0


def test_the_metadata_step_does_not_scan_the_whole_file(fixture_path: Path) -> None:
    """Aralık header'dan `O(1)` gelir: tarama süreye dahil edilmez."""
    with MappedSource(fixture_path) as source:
        buffer = source.data()
        fast = measure_metadata(buffer, verify_span=False)
        verified = measure_metadata(buffer, verify_span=True)

    assert not fast.span_verified
    # Ayni araligi verirler; dogrulama yalnizca kaniti ekler.
    assert (fast.start_ns, fast.end_ns) == (verified.start_ns, verified.end_ns)
    # Tarama sureye girseydi bu kadar hizli olamazdi (480.000 ornek cozulur).
    assert fast.seconds < 0.25


# --------------------------------------------------------------------------- #
# sorgu
# --------------------------------------------------------------------------- #


def _query_over(buffer: memoryview, channel: int = 0) -> DisplayQuery:
    def read(_channel_id: str, window: TimeRange) -> DataChunk:
        return query_acoustic_channel(buffer, channel, window)

    return DisplayQuery(read)


def test_every_viewport_width_plus_the_full_span_is_measured(
    fixture_path: Path, span: TimeRange
) -> None:
    with MappedSource(fixture_path) as source:
        buffer = source.data()
        results = measure_queries(
            _query_over(buffer),
            "0",
            span,
            viewport_seconds=DEFAULT_VIEWPORT_SECONDS,
            max_points=500,
        )

    assert [item.label for item in results] == ["0.01s", "0.1s", "1s", "10s", "full"]
    # `span_ns` pencere **genisligi**; tam kapsam 80 * 125 ms = 10 s.
    assert [item.span_ns for item in results] == [
        10_000_000,
        100_000_000,
        1_000_000_000,
        10_000_000_000,
        span.end_ns - span.start_ns,
    ]
    for item in results:
        assert item.max_points == 500
        assert 0 < item.returned_points <= 500
        assert item.duration_ms > 0.0


def test_each_query_is_measured_cold(fixture_path: Path, span: TimeRange) -> None:
    """Aynı genişlik iki kez ölçülürse ikincisi önbellekten gelmez."""
    calls: list[TimeRange] = []

    with MappedSource(fixture_path) as source:
        buffer = source.data()

        def read(_channel_id: str, window: TimeRange) -> DataChunk:
            calls.append(window)
            return query_acoustic_channel(buffer, 0, window)

        query = DisplayQuery(read)
        measure_queries(query, "0", span, viewport_seconds=(1.0, 1.0), max_points=500)

    # Iki ayni genislik + tam kapsam = uc ayri decode; hicbiri isabet degil.
    assert len(calls) == 3
    assert query.cache_stats().hits == 0


# --------------------------------------------------------------------------- #
# FPS
# --------------------------------------------------------------------------- #


def test_the_frame_rate_is_derived_from_completed_frames(
    fixture_path: Path, span: TimeRange
) -> None:
    with MappedSource(fixture_path) as source:
        result = measure_frame_rate(
            _query_over(source.data()),
            "0",
            span,
            frames=8,
            window_s=1.0,
            max_points=500,
            budget_s=120.0,
        )

    assert result.frames_requested == 8
    assert result.frames_completed == 8
    assert not result.truncated
    assert result.window_ns == 1_000_000_000
    assert abs(result.pipeline_fps - 8 / result.elapsed_s) < 1e-9
    assert 0 < result.frame_ms_p50 <= result.frame_ms_p95 <= result.frame_ms_max


def test_a_run_that_exceeds_its_budget_stops_and_says_so(
    fixture_path: Path, span: TimeRange
) -> None:
    with MappedSource(fixture_path) as source:
        result = measure_frame_rate(
            _query_over(source.data()),
            "0",
            span,
            frames=10_000,
            window_s=1.0,
            max_points=500,
            budget_s=0.0,  # ilk kareden sonra dur
        )

    assert result.truncated
    assert result.frames_completed == 1
    assert result.pipeline_fps > 0.0


def test_the_frame_run_does_not_inherit_the_full_span_cache(
    fixture_path: Path, span: TimeRange
) -> None:
    """Ölçüm sırası FPS'i şişirmemeli — `measure_queries` sonrası tam
    kapsam penceresi önbellekte kalsaydı her kare isabet olurdu."""
    calls: list[TimeRange] = []

    with MappedSource(fixture_path) as source:
        buffer = source.data()

        def read(_channel_id: str, window: TimeRange) -> DataChunk:
            calls.append(window)
            return query_acoustic_channel(buffer, 0, window)

        query = DisplayQuery(read)
        measure_queries(query, "0", span, viewport_seconds=(1.0,), max_points=500)
        assert len(calls) == 2  # 1s + tam kapsam
        measure_frame_rate(query, "0", span, frames=6, window_s=1.0, max_points=500, budget_s=120.0)

    # Alti kare de gercekten decode edildi: 2 + 6.
    assert len(calls) == 8


def test_at_least_one_frame_is_required(fixture_path: Path) -> None:
    with MappedSource(fixture_path) as source, pytest.raises(ValueError, match="frames"):
        measure_frame_rate(
            _query_over(source.data()),
            "0",
            TimeRange(0, 1_000),
            frames=0,
            window_s=1.0,
            max_points=500,
            budget_s=1.0,
        )


# --------------------------------------------------------------------------- #
# tam kosu
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def report(fixture_path: Path) -> dict[str, object]:
    return run(
        [fixture_path],
        max_points=500,
        frames=6,
        frame_window_s=1.0,
        frame_budget_s=120.0,
        viewport_seconds=(0.1, 1.0),
        cache_bytes=64 * 1024 * 1024,
        verify_span=True,
    )


def _entry(report: dict[str, object]) -> dict[str, Any]:
    """Rapordaki tek dosya girdisi; JSON `object` yığınını tiplendirir."""
    files = cast("list[dict[str, Any]]", report["files"])
    assert len(files) == 1
    return files[0]


def test_the_report_carries_the_machine_and_the_targets(report: dict[str, object]) -> None:
    assert report["benchmark"] == "large-file"
    assert report["task"] == "F4-064"
    assert set(cast("dict[str, object]", report["machine"])) == set(machine_info())
    assert (
        report["targets"]
        == TARGETS
        == {
            "metadata_seconds": 5.0,
            "query_ms": 150.0,
            "pipeline_fps": 30.0,
        }
    )
    assert "pipeline_fps excludes Qt paint" in str(report["scope"])
    assert cast(float, report["total_seconds"]) > 0.0


def test_the_report_holds_all_four_result_families(report: dict[str, object]) -> None:
    entry = _entry(report)
    assert {"metadata", "queries", "frame_rate", "memory"} <= set(entry)
    assert entry["file_bytes"] == FILE_BYTES
    assert entry["samples_per_block"] == SAMPLES_PER_BLOCK
    assert entry["channel_measured"] == 0
    assert entry["metadata"]["record_count"] == RECORDS
    assert [item["label"] for item in entry["queries"]] == ["0.1s", "1s", "full"]
    assert entry["frame_rate"]["frames_completed"] == 6
    assert entry["cache"]["max_bytes"] == 64 * 1024 * 1024


def test_the_memory_result_is_reported_against_the_file_size(report: dict[str, object]) -> None:
    entry = _entry(report)
    memory: dict[str, Any] = entry["memory"]
    file_bytes: int = entry["file_bytes"]
    assert memory["tracemalloc_retained_bytes"] > 0
    assert memory["tracemalloc_peak_bytes"] >= memory["tracemalloc_retained_bytes"]
    assert (
        abs(memory["retained_per_file_byte"] - memory["tracemalloc_retained_bytes"] / file_bytes)
        < 1e-12
    )
    assert abs(memory["peak_per_file_byte"] - memory["tracemalloc_peak_bytes"] / file_bytes) < 1e-12
    peak_ws = memory["peak_working_set_bytes"]
    assert peak_ws is None or peak_ws > 0


def test_the_report_is_json_serialisable(report: dict[str, object]) -> None:
    assert json.loads(json.dumps(report)) == report


def test_the_run_needs_at_least_one_file() -> None:
    with pytest.raises(ValueError, match="En az bir dosya"):
        run([])


def test_the_benchmark_releases_the_file(tmp_path: Path) -> None:
    """Ölçüm bittiğinde eşleme kapanır; Windows dosyayı kilitli tutmaz."""
    target = tmp_path / "released.bin"
    write_fixture(target, HEADER_BYTES + 8 * RECORD_BYTES)
    benchmark_file(target, max_points=200, frames=2, frame_window_s=0.25, frame_budget_s=30.0)
    target.unlink()
    assert not target.exists()
