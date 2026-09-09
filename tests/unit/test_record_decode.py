"""Tek Data kaydını indeksten çözme — `F2-005`.

Kabul: isim, sıra, zaman, sekiz sensör, BIT ve TX referansla eşleşir.

`F2-002`'den farkı: burada offset `caller` tarafından hesaplanmaz —
`decode_record_at_index` sıfır tabanlı **kayıt indeksinden** offseti kendi
türetir (`docs/format/timing-and-naming.md` §2: `header_size + index *
record_size`).
"""

from __future__ import annotations

import pytest
from tests.golden_bytes import (
    bit_status_for,
    build_valid_fixture,
    sensor_values,
    tx_status_for,
)

from sonar_analyzer.io.decoders.profile_a import decode_record_at_index


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    return build_valid_fixture()


@pytest.mark.parametrize("index", range(8))
def test_every_record_matches_the_reference_formula(fixture_bytes: bytes, index: int) -> None:
    """Kabul kriteri: isim, sıra, zaman, sekiz sensör, BIT ve TX referansla eşleşir."""
    record = decode_record_at_index(fixture_bytes, index)

    assert record.name.rstrip(b"\x00").decode("ascii") == f"Data{index:05d}"
    assert record.sequence_no == index
    assert record.elapsed_us == index * 125_000
    assert record.sensor_values == sensor_values(index)
    assert record.bit_status == bit_status_for(index)
    assert record.tx_status == tx_status_for(index)


def test_index_zero_and_offset_zero_agree(fixture_bytes: bytes) -> None:
    from sonar_analyzer.io.readers.binary_reader import read_data_record_v1

    by_index = decode_record_at_index(fixture_bytes, 0)
    by_offset = read_data_record_v1(fixture_bytes, offset=32)
    assert by_index == by_offset


def test_negative_index_is_rejected(fixture_bytes: bytes) -> None:
    with pytest.raises(ValueError, match="negatif olamaz"):
        decode_record_at_index(fixture_bytes, -1)


def test_index_beyond_file_raises_struct_error(fixture_bytes: bytes) -> None:
    """Sınır dışı indeks (F2-009'a kadar) en azından güvenli biçimde patlar."""
    import struct

    with pytest.raises(struct.error):
        decode_record_at_index(fixture_bytes, 999)


def test_custom_header_and_record_size_are_respected() -> None:
    """İleride farklı sözleşmeli bir dosyada da offset doğru hesaplanmalı."""
    from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1

    padding = b"\x00" * 40  # varsayimsal 40 baytlik header
    body = padding + DATA_RECORD_V1.pack(b"Data00000", 0, 0, *([1.0] * 8), 0, 0)
    record = decode_record_at_index(body, 0, header_size=40)
    assert record.sequence_no == 0
    assert record.sensor_values == (1.0,) * 8
