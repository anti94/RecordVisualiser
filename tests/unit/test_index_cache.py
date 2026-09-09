"""Cache kullanımı decoder çağrısını engelleyerek, bozulma ise yeniden üreterek doğrulanır."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.golden_bytes import build_gap_fixture, build_valid_fixture

from sonar_analyzer.io.index import cache
from sonar_analyzer.io.index.cache import load_or_build_record_index
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1


def test_second_open_uses_cache_without_decoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = build_valid_fixture()
    header = read_file_header_v1(data)
    path = tmp_path / "record.idx"
    first = load_or_build_record_index(data, header, path)

    def forbidden(*args: object) -> None:
        raise AssertionError("cache kullanilirken decoder cagrildi")

    monkeypatch.setattr(cache, "build_record_index", forbidden)
    second = load_or_build_record_index(data, header, path)
    assert not first.reused
    assert second.reused
    assert first.entries == second.entries


@pytest.mark.parametrize("contents", [b"{broken", b"\xff\xfe", b"[]", b"{}"])
def test_corrupt_cache_is_rebuilt(tmp_path: Path, contents: bytes) -> None:
    path = tmp_path / "record.idx"
    path.write_bytes(contents)
    data = build_valid_fixture()
    result = load_or_build_record_index(data, read_file_header_v1(data), path)
    assert not result.reused
    assert len(result.entries) == 8
    assert load_or_build_record_index(data, read_file_header_v1(data), path).reused


def test_changed_source_with_same_size_invalidates_cache(tmp_path: Path) -> None:
    path = tmp_path / "record.idx"
    data = build_valid_fixture()
    load_or_build_record_index(data, read_file_header_v1(data), path)
    changed = build_gap_fixture()
    assert len(changed) == len(data)
    result = load_or_build_record_index(changed, read_file_header_v1(changed), path)
    assert not result.reused
    assert [entry.sequence_no for entry in result.entries] == [0, 1, 2, 3, 4, 6, 7, 8]


def test_parser_version_invalidates_cache(tmp_path: Path) -> None:
    path = tmp_path / "record.idx"
    data = build_valid_fixture()
    header = read_file_header_v1(data)
    load_or_build_record_index(data, header, path, parser_version=1)
    assert not load_or_build_record_index(data, header, path, parser_version=2).reused
    assert load_or_build_record_index(data, header, path, parser_version=2).reused


def test_valid_json_with_altered_record_is_rebuilt(tmp_path: Path) -> None:
    path = tmp_path / "record.idx"
    data = build_valid_fixture()
    header = read_file_header_v1(data)
    expected = load_or_build_record_index(data, header, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0][1] += 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = load_or_build_record_index(data, header, path)
    assert not result.reused
    assert result.entries == expected.entries


def test_empty_recording_cache_is_reused(tmp_path: Path) -> None:
    path = tmp_path / "empty.idx"
    data = build_valid_fixture(record_count=0)
    header = read_file_header_v1(data)
    assert load_or_build_record_index(data, header, path).entries == ()
    assert load_or_build_record_index(data, header, path).reused
