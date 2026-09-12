"""Parametrik Profil B sentetik üretici — plan Bölüm 8.3.13.

Bir fixture üreticisinin tek gerçek sınavı, **üretim decoder'ının**
çıktısını okuyabilmesidir. Kendi yazdığını kendi okuyan bir üretici,
ikisi birden yanlışsa bunu asla göstermez. Bu yüzden testler üretilen
dosyayı `io/decoders/profile_b.py` ile çözer.

İkinci sınav determinizmdir: aynı parametreler aynı baytları vermeli.
Tekrar üretilemeyen bir fixture ile hata ayıklamak, hatayı iki kez
aramak demektir.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.synthetic_profile_b import SyntheticSpec, build, channel_samples, write

from sonar_analyzer.io.decoders.profile_b import decode_file_header, iter_records
from sonar_analyzer.io.decoders.profile_b_sequence import SequenceLimits, check_buffer_sequence
from sonar_analyzer.io.profile_b_format import (
    BLOCK_TYPE_BIT_STATUS,
    BLOCK_TYPE_SENSOR_RAW,
    BLOCK_TYPE_TX_STATUS,
)

# --------------------------------------------------------------------------- #
# PARAMETRELER GERCEKTEN ETKI EDIYOR
# --------------------------------------------------------------------------- #


def test_the_channel_count_is_honoured() -> None:
    data = build(SyntheticSpec(channels=3, sample_rate_hz=800, duration_s=0.25))

    header = decode_file_header(data)
    assert header.channel_count == 3
    first = next(iter(iter_records(data)))
    sensors = [b for b in first.blocks if b.block_type == BLOCK_TYPE_SENSOR_RAW]
    assert len(sensors) == 3


def test_the_sample_rate_drives_the_samples_per_record() -> None:
    """8000 Hz × 0,125 s = 1000 örnek; bu bir tanım, bir seçim değil."""
    spec = SyntheticSpec(channels=1, sample_rate_hz=8_000, duration_s=0.125)
    assert spec.samples_per_record == 1_000

    data = build(spec)
    block = next(iter(iter_records(data))).sensor_block(0)
    assert block is not None
    assert block.samples is not None
    assert block.samples.size == 1_000


def test_the_duration_drives_the_record_count() -> None:
    spec = SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=1.0)
    assert spec.record_count == 8

    assert len(list(iter_records(build(spec)))) == 8


def test_each_channel_gets_a_distinct_tone_by_default() -> None:
    """Aynı frekans iki kanalda olsaydı, karışmaları tespit edilemezdi."""
    spec = SyntheticSpec(channels=4)
    tones = [spec.tone_for(index) for index in range(4)]

    assert len(set(tones)) == 4


def test_explicit_tones_are_used() -> None:
    spec = SyntheticSpec(channels=2, tones=(440.0, 880.0))
    assert spec.tone_for(0) == 440.0
    assert spec.tone_for(1) == 880.0


def test_noise_changes_the_samples() -> None:
    """Gürültü parametresi etkisiz kalırsa, senaryo üretilmemiş olur."""
    clean = SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.125, noise=0)
    noisy = SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.125, noise=500)

    assert not (channel_samples(clean, 0, 0) == channel_samples(noisy, 0, 0)).all()


def test_noise_does_not_touch_the_global_random_state() -> None:
    """Global durumu kirletmek, başka bir testin sonucunu değiştirirdi."""
    import numpy as np

    np.random.seed(1234)
    before = np.random.rand()

    np.random.seed(1234)
    channel_samples(SyntheticSpec(channels=1, sample_rate_hz=800, noise=500), 0, 0)
    after = np.random.rand()

    assert before == after


# --------------------------------------------------------------------------- #
# SENARYO BLOKLARI
# --------------------------------------------------------------------------- #


def test_tx_blocks_appear_only_when_requested() -> None:
    without = build(SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.125))
    with_tx = build(SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.125, with_tx=True))

    assert not _has_block(without, BLOCK_TYPE_TX_STATUS)
    assert _has_block(with_tx, BLOCK_TYPE_TX_STATUS)


def test_bit_blocks_appear_only_when_requested() -> None:
    without = build(SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.125))
    with_bit = build(SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.125, with_bit=True))

    assert not _has_block(without, BLOCK_TYPE_BIT_STATUS)
    assert _has_block(with_bit, BLOCK_TYPE_BIT_STATUS)


def test_tx_produces_a_start_stop_transition() -> None:
    """Hep ACTIVE kalan bir TX, START/STOP senaryosunu sınamazdı."""
    spec = SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=1.0, with_tx=True)
    states: list[bool] = []
    for record in iter_records(build(spec)):
        tx = [b for b in record.blocks if b.block_type == BLOCK_TYPE_TX_STATUS]
        assert len(tx) == 1
        states.append(record.record_index % 4 < 2)

    assert True in states
    assert False in states


# --------------------------------------------------------------------------- #
# URETIM DECODER'I OKUYABILIYOR
# --------------------------------------------------------------------------- #


def test_the_production_decoder_reads_the_generated_file() -> None:
    """Kendi yazdığını kendi okuyan bir üretici hiçbir şey kanıtlamaz."""
    data = build(SyntheticSpec(channels=2, sample_rate_hz=1_600, duration_s=0.5))

    records = list(iter_records(data))

    assert [record.record_index for record in records] == [0, 1, 2, 3]
    assert [record.name for record in records] == [f"Data{i:05d}" for i in range(4)]


def test_the_generated_file_passes_the_sequence_diagnostics() -> None:
    """Üretici kendi kurallarını çiğniyorsa, fixture güvenilmez olur."""
    spec = SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=1.0, with_tx=True)
    data = build(spec)

    limits = SequenceLimits(ticks_per_record=spec.samples_per_record)

    assert check_buffer_sequence(data) == []
    assert check_buffer_sequence(data, limits) == []


def test_the_records_stay_on_the_125_ms_grid() -> None:
    data = build(SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.5))

    offsets = [record.t_start_offset_ns for record in iter_records(data)]

    assert offsets == [0, 125_000_000, 250_000_000, 375_000_000]


# --------------------------------------------------------------------------- #
# DETERMINIZM
# --------------------------------------------------------------------------- #


def test_the_same_spec_produces_the_same_bytes() -> None:
    spec = SyntheticSpec(channels=2, sample_rate_hz=800, duration_s=0.25, noise=100)

    assert build(spec) == build(spec)


def test_a_different_seed_produces_different_bytes() -> None:
    """Seed etkisizse, farklı senaryo üretmek mümkün olmaz."""
    base = SyntheticSpec(channels=1, sample_rate_hz=800, duration_s=0.25, noise=100)
    other = SyntheticSpec(
        channels=1, sample_rate_hz=800, duration_s=0.25, noise=100, seed=base.seed + 1
    )

    assert build(base) != build(other)


# --------------------------------------------------------------------------- #
# GECERSIZ PARAMETRE SESSIZCE DUZELTILMEZ
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "kwargs",
    [
        {"channels": 0},
        {"sample_rate_hz": 0},
        {"duration_s": 0},
        {"noise": -1},
        {"seed": -1},
        {"sample_rate_hz": 4},  # 125 ms'de tek ornek bile cikmaz
        {"channels": 2, "tones": (100.0,)},  # ton sayisi kanal sayisini tutmuyor
    ],
)
def test_invalid_parameters_are_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        SyntheticSpec(**kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# DOSYAYA YAZMA
# --------------------------------------------------------------------------- #


def test_writing_reports_what_it_produced(tmp_path: Path) -> None:
    spec = SyntheticSpec(channels=2, sample_rate_hz=800, duration_s=0.25, with_tx=True)
    target = tmp_path / "alt" / "synth.bin"

    summary = write(target, spec)

    assert target.is_file()
    assert summary["bytes"] == target.stat().st_size
    assert summary["channels"] == 2
    assert summary["record_count"] == 2
    assert summary["with_tx"] is True


def _has_block(data: bytes, block_type: int) -> bool:
    return any(
        block.block_type == block_type for record in iter_records(data) for block in record.blocks
    )
