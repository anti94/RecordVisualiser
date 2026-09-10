"""Profil B akustik boyut ve sample rate sınırları — `F4-014`.

Kabul: bozuk örnek sayısı reddedilir; 8 Hz telemetri 10 kHz (48 kHz)
akustik veri diye sunulmaz.

İki bağımsız denetim doğrulanır:

* `SAMPLE_COUNT_MISMATCH` — blok 6000 örnekten farklıysa (yapısal bozukluk).
* `SAMPLE_RATE_MISMATCH` — örnek yoğunluğundan türeyen örtük hız 48 kHz'e
  uzaksa (düşük hızlı telemetrinin akustik gibi etiketlenmesi).

Tampon üreticisi bağımsız bir referanstır: `profile_b_format` struct
sözleşmelerini doğrudan kullanır, `make_acoustic_fixture`'ın özel
yardımcılarına dayanmaz.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest
from tools.make_acoustic_fixture import build_acoustic_fixture

from sonar_analyzer.io.decoders.profile_b import DecodedBlock, iter_records
from sonar_analyzer.io.decoders.profile_b_validation import (
    AcousticLimits,
    ProfileBValidationError,
    ensure_acoustic_record,
    implied_sample_rate_hz,
    is_acoustic_record,
    issue_codes,
    rates_match,
    validate_acoustic_block,
    validate_acoustic_buffer,
)
from sonar_analyzer.io.profile_b_format import (
    ACOUSTIC_DTYPE_CODE,
    BLOCK_HEADER,
    BLOCK_TYPE_PAD,
    BLOCK_TYPE_SENSOR_RAW,
    END_MARKER,
    FILE_HEADER,
    MAGIC,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_PERIOD_NS,
    RECORD_TRAILER,
    RECORD_TRAILER_SIZE,
    SAMPLES_PER_BLOCK,
    SUPPORTED_VERSION,
    record_name,
)

# --------------------------------------------------------------------------- #
# implied_sample_rate_hz / rates_match
# --------------------------------------------------------------------------- #


def test_implied_rate_of_a_full_block_is_exactly_48khz() -> None:
    assert implied_sample_rate_hz(SAMPLES_PER_BLOCK) == 48_000.0


def test_implied_rate_of_one_sample_per_record_is_8hz() -> None:
    # Profil A telemetri kadanjı: kayıt (125 ms) başına 1 örnek → 8 Hz.
    assert implied_sample_rate_hz(1) == 8.0


def test_implied_rate_scales_linearly_with_count() -> None:
    assert implied_sample_rate_hz(1_250) == 10_000.0  # "10 kHz" senaryosu
    assert implied_sample_rate_hz(3_000) == 24_000.0


def test_implied_rate_rejects_nonpositive_period() -> None:
    with pytest.raises(ValueError, match="record_period_ns"):
        implied_sample_rate_hz(6_000, record_period_ns=0)


def test_rates_match_accepts_only_tiny_deviation() -> None:
    assert rates_match(48_000.0, 48_000.0, relative_tolerance=0.01)
    assert rates_match(47_800.0, 48_000.0, relative_tolerance=0.01)  # %0.4
    assert not rates_match(47_000.0, 48_000.0, relative_tolerance=0.01)  # %2
    assert not rates_match(8.0, 48_000.0, relative_tolerance=0.01)
    assert not rates_match(10_000.0, 48_000.0, relative_tolerance=0.01)


# --------------------------------------------------------------------------- #
# validate_acoustic_block — tek blok
# --------------------------------------------------------------------------- #


def _sensor_block(
    sample_count: int,
    *,
    channel_id: int = 0,
    dtype_code: int = ACOUSTIC_DTYPE_CODE,
    byte_offset: int = 512,
) -> DecodedBlock:
    return DecodedBlock(
        block_type=BLOCK_TYPE_SENSOR_RAW,
        channel_id=channel_id,
        dtype_code=dtype_code,
        t_offset_ns=0,
        byte_offset=byte_offset,
        samples=np.zeros(sample_count, dtype=np.int16),
    )


def test_a_full_6000_sample_block_has_no_issues() -> None:
    assert validate_acoustic_block(_sensor_block(SAMPLES_PER_BLOCK)) == []


def test_a_slightly_short_block_is_only_a_count_mismatch() -> None:
    # 5999 örnek → örtük 47992 Hz (%0.017 sapma): hız denetimi geçer,
    # yalnız sayım denetimi düşer. İki denetimin bağımsızlığını gösterir.
    issues = validate_acoustic_block(_sensor_block(SAMPLES_PER_BLOCK - 1))
    assert issue_codes(issues) == ["SAMPLE_COUNT_MISMATCH"]
    assert "5999" in issues[0].message
    assert issues[0].sample_count == 5999
    assert issues[0].byte_offset == 512


def test_telemetry_density_block_is_flagged_count_and_rate() -> None:
    # Kayıt başına 1 örnek: hem sayım hem hız bozuk. "8 Hz akustik değil."
    issues = validate_acoustic_block(_sensor_block(1))
    codes = issue_codes(issues)
    assert "SAMPLE_COUNT_MISMATCH" in codes
    assert "SAMPLE_RATE_MISMATCH" in codes
    rate_msg = next(i.message for i in issues if i.code == "SAMPLE_RATE_MISMATCH")
    assert "8" in rate_msg
    assert "48000" in rate_msg


def test_ten_khz_stream_cannot_masquerade_as_48khz_acoustic() -> None:
    # 1250 örnek/125 ms = 10 kHz — kabul kriterindeki "10 kHz veri" durumu.
    issues = validate_acoustic_block(_sensor_block(1_250))
    codes = issue_codes(issues)
    assert "SAMPLE_RATE_MISMATCH" in codes
    assert "SAMPLE_COUNT_MISMATCH" in codes
    rate_msg = next(i.message for i in issues if i.code == "SAMPLE_RATE_MISMATCH")
    assert "10000" in rate_msg or "1e+04" in rate_msg


def test_empty_block_is_only_flagged_empty() -> None:
    issues = validate_acoustic_block(_sensor_block(0))
    assert issue_codes(issues) == ["EMPTY_BLOCK"]


def test_unexpected_dtype_is_flagged() -> None:
    issues = validate_acoustic_block(_sensor_block(SAMPLES_PER_BLOCK, dtype_code=0x03))
    assert "UNEXPECTED_DTYPE" in issue_codes(issues)


def test_unknown_channel_is_flagged() -> None:
    issues = validate_acoustic_block(_sensor_block(SAMPLES_PER_BLOCK, channel_id=9))
    assert "UNKNOWN_CHANNEL" in issue_codes(issues)


def test_non_sensor_block_is_ignored() -> None:
    pad = DecodedBlock(
        block_type=BLOCK_TYPE_PAD,
        channel_id=0,
        dtype_code=0,
        t_offset_ns=0,
        byte_offset=64,
        samples=None,
    )
    assert validate_acoustic_block(pad) == []


def test_limits_are_configurable() -> None:
    # 1250 örnek başka bir profilde (10 kHz) geçerli olabilir.
    limits = AcousticLimits(expected_samples=1_250, expected_sample_rate_hz=10_000)
    assert validate_acoustic_block(_sensor_block(1_250), limits) == []


# --------------------------------------------------------------------------- #
# Bağımsız tampon üreticisi (referans)
# --------------------------------------------------------------------------- #


def _file_header(record_count: int) -> bytes:
    return FILE_HEADER.pack(
        MAGIC,
        SUPPORTED_VERSION,
        0,
        FILE_HEADER.size,
        0,  # channel_count = 0 → kayıt alanı 256'da başlar
        0,
        RECORD_PERIOD_NS,
        0,
        1_788_901_200_000_000_000,
        b"\x00" * 16,
        record_count,
        b"\x00" * 196,
        0,
    )


def _record(index: int, sample_count: int, *, channel_id: int = 0) -> bytes:
    payload = np.zeros(sample_count, dtype=np.int16).tobytes()
    block = (
        BLOCK_HEADER.pack(
            BLOCK_TYPE_SENSOR_RAW, 0, len(payload), channel_id, ACOUSTIC_DTYPE_CODE, 0, 0
        )
        + payload
    )
    block += b"\x00" * ((-len(block)) % 8)
    record_size = RECORD_HEADER_SIZE + len(block) + RECORD_TRAILER_SIZE
    header = RECORD_HEADER.pack(
        record_name(index).encode("ascii").ljust(12, b"\x00"),
        index,
        record_size,
        1,  # block_count
        0,
        index * RECORD_PERIOD_NS,
        index * sample_count,
        0,
        0,
    )
    trailer = RECORD_TRAILER.pack(0, END_MARKER)
    return header + block + trailer


def _build_buffer(sample_counts: Sequence[int], *, channel_id: int = 0) -> bytes:
    out = bytearray(_file_header(len(sample_counts)))
    for index, count in enumerate(sample_counts):
        out += _record(index, count, channel_id=channel_id)
    return bytes(out)


def test_the_reference_builder_produces_a_decodable_buffer() -> None:
    buffer = _build_buffer([SAMPLES_PER_BLOCK, SAMPLES_PER_BLOCK])
    records = list(iter_records(buffer))
    assert len(records) == 2
    block = records[0].sensor_block(0)
    assert block is not None and block.samples is not None
    assert block.samples.shape[0] == SAMPLES_PER_BLOCK


# --------------------------------------------------------------------------- #
# validate_acoustic_buffer / ensure_acoustic_record
# --------------------------------------------------------------------------- #


def test_the_real_fixture_has_no_semantic_issues() -> None:
    assert validate_acoustic_buffer(build_acoustic_fixture(4)) == []


def test_every_record_of_a_telemetry_density_buffer_is_flagged() -> None:
    buffer = _build_buffer([1, 1, 1])
    issues = validate_acoustic_buffer(buffer)
    # Kayıt başına en az iki sorun (sayım + hız); üç kayıt.
    assert len(issues) >= 6
    assert issue_codes(issues).count("SAMPLE_RATE_MISMATCH") == 3
    assert issue_codes(issues).count("SAMPLE_COUNT_MISMATCH") == 3
    # Her sorun bir kaydın blok offsetine işaret eder (hepsi ayrı).
    assert len({issue.byte_offset for issue in issues}) == 3


def test_ensure_acoustic_record_raises_on_a_bad_record() -> None:
    buffer = _build_buffer([1])
    record = next(iter(iter_records(buffer)))
    with pytest.raises(ProfileBValidationError) as excinfo:
        ensure_acoustic_record(record)
    message = str(excinfo.value)
    assert "SAMPLE_COUNT_MISMATCH" in message or "SAMPLE_RATE_MISMATCH" in message
    assert excinfo.value.byte_offset > 0


def test_ensure_acoustic_record_passes_a_valid_record() -> None:
    buffer = _build_buffer([SAMPLES_PER_BLOCK])
    record = next(iter(iter_records(buffer)))
    ensure_acoustic_record(record)  # yükseltmemeli


def test_is_acoustic_record_reflects_validation() -> None:
    good = next(iter(iter_records(_build_buffer([SAMPLES_PER_BLOCK]))))
    bad = next(iter(iter_records(_build_buffer([1]))))
    assert is_acoustic_record(good) is True
    assert is_acoustic_record(bad) is False


def test_real_fixture_records_all_pass_ensure() -> None:
    for record in iter_records(build_acoustic_fixture(3)):
        ensure_acoustic_record(record)
        assert is_acoustic_record(record)
