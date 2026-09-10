"""Profil B akustik blok format sabitleri — `F4-009`.

Kabul: kanal, sample rate, örnek sayısı ve payload boyutu tanımlıdır
(bkz. plan §8.3 / `docs/format/profile-b.md`); Profil A (§8.2) değişmez.
"""

from __future__ import annotations

from pathlib import Path

from sonar_analyzer.io import profile_a_format as pa
from sonar_analyzer.io import profile_b_format as pb

DOC = Path(__file__).resolve().parents[2] / "docs" / "format" / "profile-b.md"


def test_channels_are_defined() -> None:
    assert pb.ACOUSTIC_CHANNEL_IDS == (0, 1, 2, 3)
    assert len(pb.ACOUSTIC_CHANNELS) == 4
    for cid, path, name, unit in pb.ACOUSTIC_CHANNELS:
        assert cid in pb.ACOUSTIC_CHANNEL_IDS
        assert path.startswith("Acoustic/Hydrophone ")
        assert name.startswith("Hydrophone ")
        assert unit == "Pa"


def test_sample_rate_and_count_per_block_are_consistent() -> None:
    assert pb.ACOUSTIC_SAMPLE_RATE_HZ == 48_000
    # 125 ms penceredeki örnek sayısı = fs * 0.125
    assert round(pb.ACOUSTIC_SAMPLE_RATE_HZ * pb.RECORD_PERIOD_S) == pb.SAMPLES_PER_BLOCK
    assert pb.SAMPLES_PER_BLOCK == 6_000
    # 8 kayıt/saniye × blok başına örnek = tam sample rate
    assert 8 * pb.SAMPLES_PER_BLOCK == pb.ACOUSTIC_SAMPLE_RATE_HZ


def test_payload_size_is_derived_from_count_and_dtype() -> None:
    assert pb.ACOUSTIC_DTYPE_CODE == 0x01  # int16
    assert pb.ACOUSTIC_DTYPE_SIZE == pb.DTYPE_SIZE[pb.ACOUSTIC_DTYPE_CODE] == 2
    assert pb.ACOUSTIC_PAYLOAD_BYTES == pb.SAMPLES_PER_BLOCK * pb.ACOUSTIC_DTYPE_SIZE
    assert pb.ACOUSTIC_PAYLOAD_BYTES == 12_000
    # sample_count block_size'dan tam bölünür (alan yok, türetiliyor)
    assert pb.ACOUSTIC_PAYLOAD_BYTES % pb.ACOUSTIC_DTYPE_SIZE == 0


def test_block_stride_is_eight_byte_aligned() -> None:
    stride = pb.acoustic_block_stride()
    assert stride == pb.align8(pb.BLOCK_HEADER_SIZE + pb.ACOUSTIC_PAYLOAD_BYTES)
    assert stride % 8 == 0
    assert stride == 12_016


def test_struct_sizes_match_the_contract() -> None:
    assert pb.FILE_HEADER.size == 256
    assert pb.CHANNEL_ENTRY.size == 64
    assert pb.RECORD_HEADER.size == 48
    assert pb.BLOCK_HEADER.size == 16
    assert pb.RECORD_TRAILER.size == 8


def test_record_grid_and_naming_shared_with_profile_a() -> None:
    assert pb.RECORD_PERIOD_NS == pa.EXPECTED_PERIOD_US * 1000 == 125_000_000
    assert pb.record_name(0) == "Data00000"
    assert pb.record_name(1) == "Data00001"
    assert pb.record_name(12) == "Data00012"


def test_profile_b_magic_differs_from_profile_a() -> None:
    assert pb.MAGIC == b"SNRBIN\x1a\x00"
    assert pb.MAGIC != pa.MAGIC  # Profil A "SONARBIN" — çakışmaz


def test_profile_a_constants_are_untouched() -> None:
    # §8.2 örneği bu işten etkilenmez.
    assert pa.MAGIC == b"SONARBIN"
    assert pa.EXPECTED_RECORD_SIZE_V1 == 64
    assert pa.EXPECTED_CHANNEL_COUNT == 8


def test_doc_names_the_four_required_quantities() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "48000" in text  # sample rate
    assert "6000" in text  # örnek sayısı
    assert "12000" in text  # payload boyutu
    assert "Hydrophone 1" in text and "Hydrophone 4" in text  # kanallar
    assert "Profil A" in text and "değişmez" in text  # §8.2 korunur
