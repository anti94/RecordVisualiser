"""Eksik header ve boyut sınırları — `F2-004`.

Kabul: kesik ve tutarsız girdiler aşırı allocation veya sınır dışı okumaya
yol açmaz.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.decoders.errors import HeaderContractError, TruncatedHeaderError
from sonar_analyzer.io.decoders.limits import (
    validate_buffer_has_header,
    validate_header_contract,
)
from sonar_analyzer.io.profile_a_format import FILE_HEADER_V1, FileHeaderV1


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


# -- kesik header --------------------------------------------------------


def test_full_header_length_passes() -> None:
    validate_buffer_has_header(32)  # istisna firlatmamali
    validate_buffer_has_header(544)  # tam dosya da gecerli


def test_empty_buffer_raises_truncated_header() -> None:
    with pytest.raises(TruncatedHeaderError) as exc_info:
        validate_buffer_has_header(0)
    assert exc_info.value.available_bytes == 0
    assert exc_info.value.required_bytes == 32


def test_one_byte_short_raises() -> None:
    with pytest.raises(TruncatedHeaderError) as exc_info:
        validate_buffer_has_header(31)
    assert "31" in str(exc_info.value)
    assert "32" in str(exc_info.value)


@pytest.mark.parametrize("length", [0, 1, 10, 20, 31])
def test_various_short_lengths_all_raise(length: int) -> None:
    with pytest.raises(TruncatedHeaderError):
        validate_buffer_has_header(length)


def test_check_runs_before_struct_unpack_is_attempted() -> None:
    """Sınır dışı okuma denenmeden önce kontrol edilir: struct.error değil,
    anlamlı bir FormatError alınır."""
    with pytest.raises(TruncatedHeaderError):
        validate_buffer_has_header(len(b"\x00" * 10))


# -- sozlesme ihlalleri ----------------------------------------------------


def test_valid_contract_passes() -> None:
    validate_header_contract(make_header())  # istisna firlatmamali


def test_wrong_header_size_is_rejected() -> None:
    with pytest.raises(HeaderContractError) as exc_info:
        validate_header_contract(make_header(header_size=40))
    assert exc_info.value.byte_offset == 10
    assert "40" in str(exc_info.value)


def test_wrong_record_size_is_rejected() -> None:
    with pytest.raises(HeaderContractError) as exc_info:
        validate_header_contract(make_header(record_size=68))
    assert exc_info.value.byte_offset == 12


def test_wrong_channel_count_is_rejected() -> None:
    """channel_count != 8 reddedilir: sensor_values sabit 8 alan bekliyor."""
    with pytest.raises(HeaderContractError) as exc_info:
        validate_header_contract(make_header(channel_count=12))
    assert exc_info.value.byte_offset == 20
    assert "sensor_values" in str(exc_info.value)


def test_huge_claimed_record_size_does_not_cause_over_read() -> None:
    """Kabul kriteri: aşırı büyük claim edilen boyut sınır dışı okumaya yol
    açmaz — validate_header_contract, o değere güvenerek ileri okuma
    yapmadan reddeder."""
    header = make_header(record_size=0xFFFFFFFF)
    with pytest.raises(HeaderContractError):
        validate_header_contract(header)


def test_error_hierarchy() -> None:
    from sonar_analyzer.io.decoders.errors import FormatError

    assert issubclass(TruncatedHeaderError, FormatError)
    assert issubclass(HeaderContractError, FormatError)


def test_struct_size_stays_authoritative_regardless_of_header_claim() -> None:
    """Kayıt boyutu her zaman sabit struct'tan gelir, header'daki claim'den değil."""
    from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1

    assert DATA_RECORD_V1.size == 64
    assert FILE_HEADER_V1.size == 32
