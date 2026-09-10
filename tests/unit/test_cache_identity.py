"""Kaynak/işlem değişiklikleri kapsayan pencereye de cache isabeti veremez."""

from __future__ import annotations

import struct
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from tests.golden_bytes import build_valid_fixture

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.index.fingerprint import SourceFingerprint
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.repository.cache_identity import CacheIdentity
from sonar_analyzer.repository.display_query import DisplayQuery
from sonar_analyzer.repository.file_repository import FileRecordingRepository

CHANNEL = ChannelMetadata("a", "Sensors/A", "A", "float64", sample_rate_hz=1000)


@pytest.mark.parametrize(
    "changed",
    [
        CacheIdentity("changed-source", CHANNEL),
        CacheIdentity("source", replace(CHANNEL, calibration_id="cal-2")),
        CacheIdentity("source", replace(CHANNEL, gain=2)),
        CacheIdentity("source", replace(CHANNEL, offset=3)),
        CacheIdentity("source", replace(CHANNEL, sample_rate_hz=2000)),
        CacheIdentity("source", replace(CHANNEL, time_base_id="other-clock")),
        CacheIdentity("source", CHANNEL, parser_version=2),
        CacheIdentity("source", CHANNEL, processing_version=2),
        CacheIdentity("source", CHANNEL, summary_version=2),
    ],
)
def test_changed_context_cannot_reuse_a_covering_window(changed: CacheIdentity) -> None:
    current = CacheIdentity("source", CHANNEL)
    reads = 0

    def read(channel_id: str, span: TimeRange) -> DataChunk:
        nonlocal reads
        reads += 1
        times = np.arange(span.start_ns, span.end_ns, dtype=np.int64)
        return DataChunk(channel_id, times, np.full(times.size, float(reads)))

    query = DisplayQuery(read, identity_for=lambda _: current)
    query.query("a", TimeRange(0, 1000), 60)
    current = replace(current)  # eşdeğer nesne aynı snapshot'ı temsil eder
    assert np.all(query.query("a", TimeRange(100, 800), 40).values == 1)
    assert reads == 1
    current = changed
    assert np.all(query.query("a", TimeRange(100, 800), 40).values == 2)
    assert reads == 2


def test_processing_parameters_order_and_enabled_state_change_cached_values() -> None:
    scale = ProcessingStep.default(StepKind.SCALE, "a").with_parameters(factor=2)
    offset = ProcessingStep.default(StepKind.OFFSET, "a").with_parameters(delta=3)
    chain = ProcessingChain([scale, offset])
    reads = 0

    def read(channel_id: str, span: TimeRange) -> DataChunk:
        nonlocal reads
        reads += 1
        times = np.arange(span.start_ns, span.end_ns, dtype=np.int64)
        result = chain.run(np.ones(times.size))
        return DataChunk(channel_id, times, result.values)

    def identity(_: str) -> CacheIdentity:
        return CacheIdentity("source", CHANNEL, processing_signature=chain.signature())

    query = DisplayQuery(read, identity_for=identity)
    span = TimeRange(0, 1000)
    assert np.all(query.query("a", span, 60).values == 5)
    chain = ProcessingChain([scale.with_parameters(factor=4), offset])
    assert np.all(query.query("a", span, 60).values == 7)
    chain = ProcessingChain([offset, scale])
    assert np.all(query.query("a", span, 60).values == 8)
    chain = ProcessingChain([replace(scale, enabled=False), offset])
    assert np.all(query.query("a", span, 60).values == 4)
    assert reads == 4


def test_file_calibration_change_returns_new_physical_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "record.bin"
    source.write_bytes(build_valid_fixture(record_count=100))
    with FileRecordingRepository() as repo:
        repo.open(source)
        span = repo.metadata().time_range
        before = repo.query("ch0", span, 200)
        channels = repo.channels()
        monkeypatch.setattr(
            repo,
            "_channels",
            (replace(channels[0], calibration_id="new", gain=2, offset=3), *channels[1:]),
        )
        after = repo.query("ch0", span, 200)
        np.testing.assert_allclose(after.values, before.values * 2 + 3)


def test_same_path_same_size_changed_content_has_new_fingerprint_and_values(tmp_path: Path) -> None:
    source = tmp_path / "record.bin"
    original = build_valid_fixture(record_count=100)
    source.write_bytes(original)
    with FileRecordingRepository() as repo:
        repo.open(source)
        span = repo.metadata().time_range
        before = repo.query("ch0", span, 200)
        repo.close()
        changed = bytearray(original)
        struct.pack_into("<f", changed, 32 + 24, 1234.0)
        assert SourceFingerprint.from_bytes(changed) != SourceFingerprint.from_bytes(original)
        source.write_bytes(changed)
        repo.open(source)
        after = repo.query("ch0", span, 200)
        assert not repo.cache_reused
        assert after.values[0] == 1234.0
        assert before.values[0] != after.values[0]
        np.testing.assert_array_equal(before.values[1:], after.values[1:])
