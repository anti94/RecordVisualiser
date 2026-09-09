"""Magic ve sürüm doğrulaması — `F2-003`.

Kabul: geçersiz magic ve bilinmeyen sürüm konum bilgili hata verir.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.decoders.errors import InvalidMagicError, UnsupportedVersionError
from sonar_analyzer.io.decoders.profile_a import validate_magic, validate_version
from sonar_analyzer.io.profile_a_format import SUPPORTED_VERSIONS, FileHeaderV1


def make_header(**overrides: object) -> FileHeaderV1:
    defaults: dict[str, object] = {
        "magic": b"SONARBIN",
        "version": 1,
        "header_size": 32,
        "record_size": 64,
        "period_us": 125_000,
        "channel_count": 8,
        "start_time_utc_ns": 0,
    }
    defaults.update(overrides)
    return FileHeaderV1(**defaults)  # type: ignore[arg-type]


# -- magic -------------------------------------------------------------


def test_valid_magic_passes() -> None:
    validate_magic(make_header())  # istisna firlatmamali


def test_invalid_magic_raises_with_position() -> None:
    with pytest.raises(InvalidMagicError) as exc_info:
        validate_magic(make_header(magic=b"BADMAGIC"))

    error = exc_info.value
    assert error.byte_offset == 0
    assert error.found == b"BADMAGIC"
    assert "offset 0" in str(error)
    assert "BADMAGIC" in str(error)


def test_magic_error_reports_wrong_length_magic() -> None:
    with pytest.raises(InvalidMagicError):
        validate_magic(make_header(magic=b"SNR"))


# -- surum ------------------------------------------------------------


def test_supported_versions_pass() -> None:
    for version in SUPPORTED_VERSIONS:
        validate_version(make_header(version=version))  # istisna firlatmamali


def test_unsupported_version_raises_with_position() -> None:
    with pytest.raises(UnsupportedVersionError) as exc_info:
        validate_version(make_header(version=99))

    error = exc_info.value
    assert error.byte_offset == 8
    assert error.found == 99
    assert "99" in str(error)
    assert "offset 8" in str(error)


def test_unsupported_version_message_lists_supported_versions() -> None:
    with pytest.raises(UnsupportedVersionError) as exc_info:
        validate_version(make_header(version=0))
    assert "1" in str(exc_info.value)
    assert "2" in str(exc_info.value)


# -- hiyerarsi ----------------------------------------------------------


def test_both_errors_are_format_errors() -> None:
    from sonar_analyzer.io.decoders.errors import FormatError

    assert issubclass(InvalidMagicError, FormatError)
    assert issubclass(UnsupportedVersionError, FormatError)
    assert issubclass(FormatError, ValueError)
