"""Event/BIT metadata'sının JSON dışa aktarımı — `F4-084`.

Kabul: seçili aralık ve domain alanları kayıpsız çıkar.

"Kayıpsız" iki şekilde denetlenir: her domain alanının belgede karşılığı
olduğu **alan adları karşılaştırılarak** (yeni bir alan eklenirse test
düşer), ve değerlerin tipiyle birlikte geri okunabildiği gösterilerek —
`None` atlanmaz, sayı metne dönmez, `int64` tam sayı kalır.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from sonar_analyzer.domain.event import BitResult, BitState, Event, Severity
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.export.json_export import (
    EXPORT_SCHEMA_VERSION,
    JsonExportError,
    bit_result_to_dict,
    build_document,
    event_to_dict,
    utc_iso,
    write_metadata_json,
)

S = 1_000_000_000
T0 = 1_788_901_200_000_000_000


def _event(offset_s: int = 0, **overrides: object) -> Event:
    fields: dict[str, object] = {
        "timestamp_ns": T0 + offset_s * S,
        "source": "BIT",
        "category": "Thermal Management",
        "severity": Severity.ERROR,
        "code": "E-102",
        "message": "Sicaklik esigi asildi",
        "state": "FAIL",
        "value": 87.5,
        "unit": "°C",
        "source_offset": 4096,
    }
    fields.update(overrides)
    return Event(**fields)  # type: ignore[arg-type]


def _bit(offset_s: int = 0, **overrides: object) -> BitResult:
    fields: dict[str, object] = {
        "timestamp_ns": T0 + offset_s * S,
        "test_id": 3,
        "component": "Thermal Management",
        "state": BitState.FAIL,
        "severity": Severity.ERROR,
        "code": 102,
        "measured": 87.5,
        "unit": "°C",
        "detail": "esik 85",
    }
    fields.update(overrides)
    return BitResult(**fields)  # type: ignore[arg-type]


RECORDING = RecordingMetadata(
    recording_id="rec-1",
    source_path="D:/kayit.bin",
    time_range=TimeRange(T0, T0 + 10 * S),
    device_id="sonar-7",
    firmware_version="1.2.3",
    channel_count=8,
    record_count=80,
    file_size_bytes=123456,
    diagnostics=["Bu format CRC icermiyor"],
)


# --------------------------------------------------------------------------- #
# DOMAIN ALANLARI kayipsiz
# --------------------------------------------------------------------------- #


def test_every_event_field_appears_in_the_document() -> None:
    """Yeni bir domain alanı eklenirse bu test düşer — kasıtlı."""
    payload = event_to_dict(_event())
    domain_fields = {field.name for field in dataclasses.fields(Event)}
    assert domain_fields <= set(payload)
    # Okunabilirlik icin bir de ISO zaman eklenir.
    assert set(payload) - domain_fields == {"timestamp_utc"}


def test_every_bit_field_appears_in_the_document() -> None:
    payload = bit_result_to_dict(_bit())
    domain_fields = {field.name for field in dataclasses.fields(BitResult)}
    assert domain_fields <= set(payload)
    assert set(payload) - domain_fields == {"timestamp_utc"}


def test_event_values_keep_their_types() -> None:
    payload = json.loads(json.dumps(event_to_dict(_event())))
    assert payload["timestamp_ns"] == T0
    assert isinstance(payload["timestamp_ns"], int)
    assert payload["value"] == 87.5
    assert isinstance(payload["value"], float)
    assert payload["source_offset"] == 4096
    assert payload["severity"] == "error"
    assert payload["unit"] == "°C"


def test_a_text_valued_event_stays_text() -> None:
    """`value` sayı da metin de olabilir; ayrım korunmalı."""
    payload = json.loads(json.dumps(event_to_dict(_event(value="LOCKED"))))
    assert payload["value"] == "LOCKED"
    assert isinstance(payload["value"], str)


def test_empty_fields_are_written_as_null_not_dropped() -> None:
    """ "Alan yoktu" ile "alan boştu" karışmamalı."""
    payload = event_to_dict(_event(state=None, value=None, unit=None, source_offset=None))
    for key in ("state", "value", "unit", "source_offset"):
        assert key in payload
        assert payload[key] is None


def test_bit_values_keep_their_types() -> None:
    payload = json.loads(json.dumps(bit_result_to_dict(_bit())))
    assert payload["test_id"] == 3
    assert payload["state"] == "fail"
    assert payload["measured"] == 87.5
    assert payload["code"] == 102


def test_a_bit_result_without_a_measurement_keeps_the_null() -> None:
    payload = bit_result_to_dict(_bit(measured=None, unit=None))
    assert payload["measured"] is None
    assert payload["unit"] is None


def test_the_canonical_time_survives_the_iso_rendering() -> None:
    """ISO gösterimi yardımcıdır; kanonik değer `timestamp_ns`."""
    odd = T0 + 123_456_789  # mikrosaniye alti kisim var
    payload = event_to_dict(_event(timestamp_ns=odd))
    assert payload["timestamp_ns"] == odd
    assert payload["timestamp_utc"] == utc_iso(odd)
    assert payload["timestamp_utc"].endswith("+00:00")


def test_unicode_text_survives_json() -> None:
    message = "Sıcaklık eşiği aşıldı — 87,5 °C 🔥"
    payload = json.loads(json.dumps(event_to_dict(_event(message=message)), ensure_ascii=False))
    assert payload["message"] == message


# --------------------------------------------------------------------------- #
# SECILI ARALIK
# --------------------------------------------------------------------------- #


def test_the_document_records_the_exported_range() -> None:
    span = TimeRange(T0 + S, T0 + 5 * S)
    document = build_document([], [], exported_range=span)
    recorded = document["range"]
    assert recorded["start_ns"] == span.start_ns
    assert recorded["end_ns"] == span.end_ns
    assert recorded["duration_ns"] == 4 * S
    assert recorded["start_utc"] == utc_iso(span.start_ns)


def test_without_a_range_the_field_is_explicitly_null() -> None:
    assert build_document([], [])["range"] is None


def test_records_outside_the_range_are_left_out() -> None:
    events = [_event(0), _event(2), _event(6)]
    document = build_document(events, [], exported_range=TimeRange(T0 + S, T0 + 5 * S))
    assert document["counts"]["events"] == 1
    assert document["events"][0]["timestamp_ns"] == T0 + 2 * S


def test_the_range_is_half_open() -> None:
    """Başlangıç dahil, bitiş hariç — `TimeRange` ile aynı sözleşme."""
    events = [_event(1), _event(5)]
    document = build_document(events, [], exported_range=TimeRange(T0 + S, T0 + 5 * S))
    assert [item["timestamp_ns"] for item in document["events"]] == [T0 + S]


def test_bit_results_are_filtered_by_the_same_range() -> None:
    bits = [_bit(0), _bit(3), _bit(9)]
    document = build_document([], bits, exported_range=TimeRange(T0 + S, T0 + 5 * S))
    assert document["counts"]["bit_results"] == 1
    assert document["bit_results"][0]["timestamp_ns"] == T0 + 3 * S


def test_without_a_range_everything_is_exported() -> None:
    document = build_document([_event(0), _event(50)], [_bit(0)])
    assert document["counts"] == {"events": 2, "bit_results": 1}


def test_records_come_out_in_time_order() -> None:
    document = build_document([_event(5), _event(1), _event(3)], [])
    stamps = [item["timestamp_ns"] for item in document["events"]]
    assert stamps == sorted(stamps)


# --------------------------------------------------------------------------- #
# kayit ust bilgisi
# --------------------------------------------------------------------------- #


def test_the_recording_metadata_is_carried() -> None:
    recorded = build_document([], [], recording=RECORDING)["recording"]
    assert recorded["recording_id"] == "rec-1"
    assert recorded["source_path"] == "D:/kayit.bin"
    assert recorded["device_id"] == "sonar-7"
    assert recorded["firmware_version"] == "1.2.3"
    assert recorded["channel_count"] == 8
    assert recorded["file_size_bytes"] == 123456
    assert recorded["diagnostics"] == ["Bu format CRC icermiyor"]


def test_an_absent_recording_is_explicitly_null() -> None:
    assert build_document([], [])["recording"] is None


def test_blank_optional_recording_fields_become_null() -> None:
    plain = RecordingMetadata(recording_id="r", source_path="p", time_range=TimeRange(0, S))
    recorded = build_document([], [], recording=plain)["recording"]
    assert recorded["device_id"] is None
    assert recorded["firmware_version"] is None


def test_the_document_names_its_schema() -> None:
    document = build_document([], [])
    assert document["schema_version"] == EXPORT_SCHEMA_VERSION == 1
    assert document["kind"] == "event-bit-metadata"


# --------------------------------------------------------------------------- #
# dosyaya yazma
# --------------------------------------------------------------------------- #


def test_writing_produces_readable_json(tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"
    result = write_metadata_json(
        [_event(0), _event(2)],
        [_bit(1)],
        target,
        recording=RECORDING,
        exported_range=TimeRange(T0, T0 + 5 * S),
    )

    assert result.path == target
    assert (result.event_count, result.bit_count) == (2, 1)
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["counts"] == {"events": 2, "bit_results": 1}
    assert document["events"][0]["code"] == "E-102"


def test_the_written_file_round_trips_every_field(tmp_path: Path) -> None:
    """Yazılan belge, bellekteki belgeyle birebir aynı."""
    target = tmp_path / "metadata.json"
    events, bits = [_event(0)], [_bit(0)]
    write_metadata_json(events, bits, target, recording=RECORDING)

    assert json.loads(target.read_text(encoding="utf-8")) == json.loads(
        json.dumps(build_document(events, bits, recording=RECORDING))
    )


def test_a_missing_directory_is_created(tmp_path: Path) -> None:
    target = tmp_path / "cikti" / "metadata.json"
    write_metadata_json([], [], target)
    assert target.exists()


def test_no_partial_file_is_left_behind(tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"
    write_metadata_json([_event(0)], [], target)
    assert not target.with_name(target.name + ".partial").exists()


def test_writing_over_an_existing_file_replaces_it(tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"
    write_metadata_json([_event(0), _event(1)], [], target)
    write_metadata_json([_event(0)], [], target)
    assert json.loads(target.read_text(encoding="utf-8"))["counts"]["events"] == 1


def test_a_directory_target_is_refused(tmp_path: Path) -> None:
    with pytest.raises(JsonExportError, match="bir dizin"):
        write_metadata_json([], [], tmp_path)


def test_the_file_ends_with_a_newline(tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"
    write_metadata_json([], [], target)
    assert target.read_text(encoding="utf-8").endswith("\n")


def test_an_empty_selection_still_writes_a_valid_document(tmp_path: Path) -> None:
    target = tmp_path / "metadata.json"
    result = write_metadata_json([], [], target, exported_range=TimeRange(T0, T0 + S))
    assert (result.event_count, result.bit_count) == (0, 0)
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["events"] == []
    assert document["range"]["duration_ns"] == S
