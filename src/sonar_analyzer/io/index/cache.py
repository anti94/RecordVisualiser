"""Kaynak ve parser sürümü değişmediyse kayıt indeksini yeniden kullan — F2-032."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sonar_analyzer.io.index.fingerprint import PARSER_VERSION, SourceFingerprint
from sonar_analyzer.io.index.record_index import RecordIndexEntry, build_record_index
from sonar_analyzer.io.index.storage import load_index_json, save_index_atomic
from sonar_analyzer.io.profile_a_format import FileHeaderV1
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer

INDEX_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CachedRecordIndex:
    entries: tuple[RecordIndexEntry, ...]
    reused: bool
    fingerprint: SourceFingerprint


def _records_digest(records: object) -> str:
    encoded = json.dumps(records, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _restore(
    payload: dict[str, Any],
    fingerprint: SourceFingerprint,
    header: FileHeaderV1,
    parser_version: int,
) -> tuple[RecordIndexEntry, ...] | None:
    for key, expected in (
        ("schema_version", INDEX_SCHEMA_VERSION),
        ("parser_version", parser_version),
        ("file_size", fingerprint.file_size),
    ):
        if type(payload.get(key)) is not int or payload[key] != expected:
            return None
    if payload.get("source_sha256") != fingerprint.content_sha256:
        return None
    raw: Any = payload.get("records")
    if not isinstance(raw, list):
        return None
    records = cast(list[Any], raw)
    expected_count = (fingerprint.file_size - header.header_size) // header.record_size
    if len(records) != expected_count:
        return None
    if payload.get("records_sha256") != _records_digest(records):
        return None
    result: list[RecordIndexEntry] = []
    for index, item in enumerate(records):
        if not isinstance(item, list):
            return None
        fields = cast(list[Any], item)
        if len(fields) != 3 or any(type(value) is not int for value in fields):
            return None
        sequence, offset, timestamp = cast(tuple[int, int, int], tuple(fields))
        if not 0 <= sequence <= 0xFFFFFFFF or timestamp < 0:
            return None
        if offset != header.header_size + index * header.record_size:
            return None
        result.append(RecordIndexEntry(sequence, offset, timestamp))
    return tuple(result)


def load_or_build_record_index(
    data: ReadableBuffer,
    header: FileHeaderV1,
    cache_path: Path,
    *,
    parser_version: int = PARSER_VERSION,
) -> CachedRecordIndex:
    """Geçersiz/eski cache'i yeniden üretir; sağlam cache'te decoder taraması yapmaz.

    Çağıran header sözleşmesini önceden doğrular. Cache kaynak dosyanın kendisi
    olamaz. İndeks içeriğinin ayrı özeti, geçerli JSON'daki kazara değişimi yakalar.
    """
    fingerprint = SourceFingerprint.from_bytes(data)
    payload = load_index_json(cache_path)
    if payload is not None:
        try:
            entries = _restore(payload, fingerprint, header, parser_version)
        except (ValueError, TypeError, OverflowError, RecursionError):
            entries = None
        if entries is not None:
            return CachedRecordIndex(entries, reused=True, fingerprint=fingerprint)

    entries = tuple(build_record_index(data, header))
    records = [[entry.sequence_no, entry.byte_offset, entry.timestamp_ns] for entry in entries]
    save_index_atomic(
        cache_path,
        {
            "schema_version": INDEX_SCHEMA_VERSION,
            "parser_version": parser_version,
            "file_size": fingerprint.file_size,
            "source_sha256": fingerprint.content_sha256,
            "records": records,
            "records_sha256": _records_digest(records),
        },
    )
    return CachedRecordIndex(entries, reused=False, fingerprint=fingerprint)
