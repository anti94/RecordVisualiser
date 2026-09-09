"""Kaynak fingerprint ve parser sürümünü kaydetme — `F2-030`.

Kabul: kaynak değişikliği veya decoder değişikliği indeksi geçersiz kılar.
"""

from __future__ import annotations

from pathlib import Path

from tests.golden_bytes import VALID_8RECORDS_SHA256, build_valid_fixture

from sonar_analyzer.io.index.fingerprint import (
    PARSER_VERSION,
    IndexProvenance,
    SourceFingerprint,
)


def test_fingerprint_matches_documented_sha256() -> None:
    data = build_valid_fixture()
    fingerprint = SourceFingerprint.from_bytes(data)

    assert fingerprint.file_size == 544
    assert fingerprint.content_sha256 == VALID_8RECORDS_SHA256


def test_provenance_is_valid_for_unchanged_source() -> None:
    data = build_valid_fixture()
    provenance = IndexProvenance.current(data)

    assert provenance.is_valid_for(data) is True


def test_source_change_invalidates_the_index() -> None:
    """Kabul kriteri (ilk yarı): kaynak değişikliği indeksi geçersiz kılar."""
    original = build_valid_fixture()
    provenance = IndexProvenance.current(original)

    modified = bytearray(original)
    modified[100] ^= 0xFF  # tek bayt bile yeterli

    assert provenance.is_valid_for(bytes(modified)) is False


def test_decoder_version_change_invalidates_the_index() -> None:
    """Kabul kriteri (ikinci yarı): decoder değişikliği indeksi geçersiz kılar."""
    data = build_valid_fixture()
    provenance = IndexProvenance.current(data)

    assert provenance.is_valid_for(data, parser_version=PARSER_VERSION + 1) is False


def test_both_source_and_decoder_change_still_invalidates() -> None:
    data = build_valid_fixture()
    provenance = IndexProvenance.current(data)

    modified = bytearray(data)
    modified[0] ^= 0xFF

    assert provenance.is_valid_for(bytes(modified), parser_version=PARSER_VERSION + 1) is False


def test_different_source_with_same_size_still_detected() -> None:
    """Boyut ayni kalsa da icerik farkliysa hash farkli olur."""
    data = build_valid_fixture()
    fingerprint = SourceFingerprint.from_bytes(data)

    modified = bytearray(data)
    modified[-1] ^= 0x01  # boyut degismez, son bayt degisir
    modified_fingerprint = SourceFingerprint.from_bytes(bytes(modified))

    assert fingerprint.file_size == modified_fingerprint.file_size
    assert fingerprint.content_sha256 != modified_fingerprint.content_sha256


def test_provenance_from_path_matches_from_bytes(tmp_path: Path) -> None:
    data = build_valid_fixture()
    file_path = tmp_path / "valid.bin"
    file_path.write_bytes(data)

    from_path = SourceFingerprint.from_path(file_path)
    from_bytes = SourceFingerprint.from_bytes(data)

    assert from_path == from_bytes


def test_fingerprint_and_provenance_are_immutable() -> None:
    import dataclasses

    import pytest

    fingerprint = SourceFingerprint(file_size=1, content_sha256="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        fingerprint.file_size = 2  # type: ignore[misc]

    provenance = IndexProvenance(fingerprint=fingerprint, parser_version=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        provenance.parser_version = 2  # type: ignore[misc]
