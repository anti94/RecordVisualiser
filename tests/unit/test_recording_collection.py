"""Aynı kanal ve olaylara sahip dosyalar birlikte açıldığında kimlikler ayrıdır."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from tests.golden_bytes import build_valid_fixture

from sonar_analyzer.repository.protocol import EventFilter
from sonar_analyzer.repository.recording_collection import RecordingCollection


def create_pair(tmp_path: Path) -> tuple[Path, Path]:
    first, second = tmp_path / "a" / "same.bin", tmp_path / "b" / "same.bin"
    for path in (first, second):
        path.parent.mkdir()
        path.write_bytes(build_valid_fixture())
    return first, second


def test_channels_and_events_do_not_collide(tmp_path: Path) -> None:
    first, second = create_pair(tmp_path)
    collection = RecordingCollection()
    first_id, second_id = collection.open(first), collection.open(second)
    assert first_id != second_id
    channels = collection.channels()
    assert len(channels) == len({channel.id for channel in channels}) == 16
    span = collection.get(first_id).metadata().time_range
    events = collection.events(span, EventFilter(categories=["BIT"]))
    assert len(events) == len({item.key for item in events}) == 4
    assert {item.recording_id for item in events} == {first_id, second_id}
    assert all(item.event.source == "BIT" for item in events)


def test_query_routes_to_the_correct_source(tmp_path: Path) -> None:
    first, second = create_pair(tmp_path)
    data = bytearray(second.read_bytes())
    struct.pack_into("<f", data, 32 + 24, 999.0)
    second.write_bytes(data)
    collection = RecordingCollection()
    first_id, second_id = collection.open(first), collection.open(second)
    span = collection.get(first_id).metadata().time_range
    assert collection.query(f"{first_id}:ch0", span).values[0] == 100.0
    chunk = collection.query(f"{second_id}:ch0", span)
    assert chunk.values[0] == 999.0
    assert chunk.channel_id == f"{second_id}:ch0"


def test_closing_one_source_preserves_other(tmp_path: Path) -> None:
    first, second = create_pair(tmp_path)
    collection = RecordingCollection()
    first_id, second_id = collection.open(first), collection.open(second)
    closed = collection.get(first_id)
    collection.close(first_id)
    with pytest.raises(RuntimeError):
        closed.metadata()
    assert collection.get(second_id).metadata().record_count == 8
    assert len(collection.channels()) == 8
    collection.close_all()
    assert collection.recordings() == ()


def test_reopen_replaces_snapshot_without_duplicating_source(tmp_path: Path) -> None:
    first, _ = create_pair(tmp_path)
    collection = RecordingCollection()
    identifier = collection.open(first)
    previous = collection.get(identifier)
    first.write_bytes(build_valid_fixture(2))
    assert collection.open(first) == identifier
    assert len(collection.recordings()) == 1
    assert collection.get(identifier).metadata().record_count == 2
    with pytest.raises(RuntimeError):
        previous.metadata()


def test_failed_open_preserves_collection(tmp_path: Path) -> None:
    first, _ = create_pair(tmp_path)
    collection = RecordingCollection()
    identifier = collection.open(first)
    with pytest.raises(FileNotFoundError):
        collection.open(tmp_path / "missing.bin")
    assert collection.get(identifier).metadata().record_count == 8
