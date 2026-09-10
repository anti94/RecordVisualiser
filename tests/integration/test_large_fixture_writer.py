"""Büyük fixture yolu aynı CRC sözleşmesini sınırlı bellekle üretir."""

from __future__ import annotations

import hashlib
import json
import tracemalloc
from pathlib import Path

import pytest
from tools.make_acoustic_fixture import ACOUSTIC_8RECORDS_SHA256, iter_acoustic_fixture
from tools.make_synthetic_bin import HEADER_BYTES, RECORD_BYTES, specification, write_fixture


@pytest.mark.parametrize(
    ("size", "records", "actual"),
    [(10**9, 20782, 1000030352), (10**10, 207814, 10000010192), (2 * 10**10, 415628, 20000019872)],
)
def test_planned_sizes_have_exact_record_counts(size: int, records: int, actual: int) -> None:
    spec = specification(size)
    assert spec["record_count"] == records
    assert spec["file_bytes"] == actual


def test_streaming_zero_seed_preserves_the_golden_file(tmp_path: Path) -> None:
    output = tmp_path / "golden.bin"
    result = write_fixture(output, HEADER_BYTES + 8 * RECORD_BYTES, seed=0)
    assert result["sha256"] == ACOUSTIC_8RECORDS_SHA256
    assert hashlib.sha256(output.read_bytes()).hexdigest() == result["sha256"]
    assert json.loads(output.with_name(output.name + ".json").read_text()) == result
    assert not output.with_name(output.name + ".partial").exists()


def test_seed_is_reproducible_and_changes_the_payload() -> None:
    first = b"".join(iter_acoustic_fixture(2, seed=1))
    assert first == b"".join(iter_acoustic_fixture(2, seed=1))
    assert first != b"".join(iter_acoustic_fixture(2, seed=2))


def test_streaming_does_not_retain_previous_records(tmp_path: Path) -> None:
    output = tmp_path / "bounded.bin"
    tracemalloc.start()
    try:
        write_fixture(output, HEADER_BYTES + 200 * RECORD_BYTES)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert output.stat().st_size > 9_000_000
    assert peak < 2_000_000


def test_existing_output_and_interrupted_output_are_not_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "existing.bin"
    output.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        write_fixture(output, 100_000)
    assert output.read_bytes() == b"keep"
    partial_target = tmp_path / "interrupted.bin"
    partial = tmp_path / "interrupted.bin.partial"
    partial.write_bytes(b"incomplete")
    with pytest.raises(FileExistsError):
        write_fixture(partial_target, 100_000)
    assert partial.read_bytes() == b"incomplete"
    assert not partial_target.exists()
