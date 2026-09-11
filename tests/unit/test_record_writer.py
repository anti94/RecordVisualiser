"""`DataNNNNN` kayıt serileştirmesi — `F5-026`.

Kabul: **ad, sıra, elapsed_us, payload ve varsa CRC decoder ile eşleşir.**

Her alan üretim decoder'ıyla (`read_data_record_v1`/`v2`) geri okunup
karşılaştırılır — yazıcının kendi iddiasıyla değil, okuyanın gördüğüyle.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.decoders.crc import record_crc32
from sonar_analyzer.io.decoders.crc_validation import check_record_crc
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_CHANNEL_COUNT,
    EXPECTED_RECORD_SIZE_V1,
    EXPECTED_RECORD_SIZE_V2,
    record_name,
)
from sonar_analyzer.io.readers.binary_reader import read_data_record_v1, read_data_record_v2
from sonar_analyzer.recording.record_writer import (
    NAME_FIELD_BYTES,
    build_data_record,
    encoded_record_name,
)

VALUES = (1.5, -2.25, 0.0, 100.0, -0.5, 3.75, 42.0, -17.125)


def _record(**overrides: object) -> bytes:
    kwargs: dict[str, object] = {
        "sequence_no": 7,
        "elapsed_us": 875_000,
        "sensor_values": VALUES,
    }
    kwargs.update(overrides)
    return build_data_record(**kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# her alan DECODER ile eslesir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("version", [1, 2])
def test_every_field_round_trips_through_the_production_decoder(version: int) -> None:
    raw = _record(version=version, bit_status=0x0F, tx_status=1)
    record = read_data_record_v1(raw, 0)

    assert record.name.rstrip(b"\x00").decode("ascii") == "Data00007"
    assert record.sequence_no == 7
    assert record.elapsed_us == 875_000
    # VALUES'in hepsi ikinin kuvvetlerinden kuruludur; float32'de **tam**
    # temsil edilir, bu yuzden tolerans degil tam esitlik beklenir.
    assert record.sensor_values == VALUES
    assert record.bit_status == 0x0F
    assert record.tx_status == 1


@pytest.mark.parametrize(
    ("version", "size"), [(1, EXPECTED_RECORD_SIZE_V1), (2, EXPECTED_RECORD_SIZE_V2)]
)
def test_the_record_size_matches_the_format_contract(version: int, size: int) -> None:
    assert len(_record(version=version)) == size


def test_the_name_comes_from_the_shared_naming_rule() -> None:
    """Ad, okuma tarafının beklediği adla **aynı fonksiyondan** gelir."""
    for sequence_no in (0, 1, 42, 99_999, 100_000):
        raw = _record(sequence_no=sequence_no)
        decoded = read_data_record_v1(raw, 0).name.rstrip(b"\x00").decode("ascii")
        assert decoded == record_name(sequence_no)


def test_the_name_field_is_padded_to_twelve_bytes() -> None:
    encoded = encoded_record_name(7)
    assert len(encoded) == NAME_FIELD_BYTES
    assert encoded.startswith(b"Data00007")
    assert encoded.endswith(b"\x00\x00\x00")


def test_a_name_that_would_not_fit_is_refused() -> None:
    """Ad sarmaz (`timing-and-naming.md` §2); 12 baytı aşarsa sessizce kesilmez."""
    with pytest.raises(ValueError, match="12 bayta sigmiyor"):
        encoded_record_name(10**9)


def test_negative_values_and_zero_survive_exactly() -> None:
    raw = _record(sensor_values=(0.0, -0.0, -1.0, 1.0, -1e6, 1e6, -0.125, 0.125))
    values = read_data_record_v1(raw, 0).sensor_values
    assert values[0] == 0.0
    assert values[2] == -1.0
    assert values[6] == -0.125


# --------------------------------------------------------------------------- #
# surum 2: CRC decoder tarafindan dogrulanir
# --------------------------------------------------------------------------- #


def test_the_v2_record_carries_a_crc_over_everything_before_it() -> None:
    raw = _record(version=2)
    stored = int.from_bytes(raw[-4:], "little")
    assert stored == record_crc32(raw[:-4])


def test_the_decoder_accepts_the_written_v2_crc() -> None:
    """Üretim doğrulayıcısı yazılan kaydı **geçerli** buluyor."""
    raw = _record(version=2)
    record = read_data_record_v2(raw, 0)
    assert check_record_crc(record, raw[:EXPECTED_RECORD_SIZE_V1], 0) is None


def test_the_decoder_rejects_a_corrupted_v2_record() -> None:
    raw = bytearray(_record(version=2))
    raw[20] ^= 0xFF  # payload'in ortasinda bir bayt bozuldu

    record = read_data_record_v2(bytes(raw), 0)
    assert check_record_crc(record, bytes(raw[:EXPECTED_RECORD_SIZE_V1]), 0) is not None


def test_the_v1_record_has_no_crc_field() -> None:
    assert len(_record(version=1)) == EXPECTED_RECORD_SIZE_V1


def test_the_crc_changes_when_any_field_changes() -> None:
    base = _record(version=2)
    assert _record(version=2, sequence_no=8)[-4:] != base[-4:]
    assert _record(version=2, elapsed_us=1_000_000)[-4:] != base[-4:]
    assert _record(version=2, bit_status=1)[-4:] != base[-4:]


# --------------------------------------------------------------------------- #
# belirlenimcilik ve dogrulama
# --------------------------------------------------------------------------- #


def test_the_same_inputs_always_produce_the_same_bytes() -> None:
    assert _record() == _record()


@pytest.mark.parametrize("version", [0, 3, -1])
def test_an_unsupported_version_is_refused(version: int) -> None:
    with pytest.raises(ValueError, match="Desteklenmeyen format surumu"):
        _record(version=version)


def test_a_negative_sequence_number_is_refused() -> None:
    with pytest.raises(ValueError, match="sequence_no negatif olamaz"):
        _record(sequence_no=-1)


def test_a_negative_elapsed_time_is_refused() -> None:
    with pytest.raises(ValueError, match="elapsed_us negatif olamaz"):
        _record(elapsed_us=-1)


@pytest.mark.parametrize("count", [0, 4, 7, 9, 16])
def test_a_wrong_channel_count_is_refused(count: int) -> None:
    """Profil A kayıt düzeni tam 8 kanal tutar; eksik/fazla değer kabul edilmez."""
    with pytest.raises(ValueError, match=f"{EXPECTED_CHANNEL_COUNT} deger tasimali"):
        _record(sensor_values=tuple(float(i) for i in range(count)))


def test_a_sequence_of_records_decodes_at_its_own_offset() -> None:
    """Arka arkaya yazılan kayıtlar, offsetlerinden tek tek çözülür."""
    blob = b"".join(
        build_data_record(
            sequence_no=index, elapsed_us=index * 125_000, sensor_values=VALUES, version=1
        )
        for index in range(5)
    )
    for index in range(5):
        record = read_data_record_v1(blob, index * EXPECTED_RECORD_SIZE_V1)
        assert record.sequence_no == index
        assert record.elapsed_us == index * 125_000
