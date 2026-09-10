"""ADR-010 kanıt sondasının doğruluğu ve sınırlılığı — `F4-067`.

Sonda ADR-010'un dayandığı iddiayı taşır: darboğaz native hız eksikliği
değil, sorgunun sınırsız olmasıdır. İddianın işe yaraması iki şeye bağlı —
sınırlı okuma referans decoder'la **aynı sonucu** vermeli ve dosya
büyürken **daha fazla iş yapmamalı**. İkisi de burada denetlenir; zamana
bakılmaz (zaman ölçümü `docs/adr/ADR-010-native-acceleration.md`'de,
makine bilgisiyle kayıtlıdır).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from tools.bounded_query_probe import bounded_query, record_span
from tools.make_synthetic_bin import HEADER_BYTES, RECORD_BYTES, write_fixture

from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.profile_b import ProfileBHeader, decode_file_header
from sonar_analyzer.io.decoders.profile_b_query import query_acoustic_channel
from sonar_analyzer.io.profile_b_format import RECORD_PERIOD_NS
from sonar_analyzer.io.readers.mapped_source import MappedSource

SMALL_RECORDS = 40
LARGE_RECORDS = 400


@pytest.fixture(scope="module")
def small(tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("probe") / "small.bin"
    write_fixture(target, HEADER_BYTES + SMALL_RECORDS * RECORD_BYTES)
    return target


@pytest.fixture(scope="module")
def large(tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("probe") / "large.bin"
    write_fixture(target, HEADER_BYTES + LARGE_RECORDS * RECORD_BYTES)
    return target


def _header(path: Path) -> ProfileBHeader:
    with MappedSource(path) as source:
        return decode_file_header(source.data())


# --------------------------------------------------------------------------- #
# dokunulan kayit araligi
# --------------------------------------------------------------------------- #


def test_the_record_span_is_computed_without_scanning(small: Path) -> None:
    header = _header(small)
    start = header.t0_utc_ns + 4 * RECORD_PERIOD_NS
    # Tam iki kayit genisliginde bir pencere iki kayda dokunur.
    assert record_span(header, TimeRange(start, start + 2 * RECORD_PERIOD_NS)) == (4, 6)


def test_a_window_inside_one_record_touches_one_record(small: Path) -> None:
    header = _header(small)
    start = header.t0_utc_ns + 3 * RECORD_PERIOD_NS + 1_000_000
    assert record_span(header, TimeRange(start, start + 10_000_000)) == (3, 4)


def test_the_span_is_clamped_to_the_recording(small: Path) -> None:
    header = _header(small)
    before = header.t0_utc_ns - 10 * RECORD_PERIOD_NS
    after = header.t0_utc_ns + 10_000 * RECORD_PERIOD_NS
    assert record_span(header, TimeRange(before, before + 1)) == (0, 0)
    assert record_span(header, TimeRange(after, after + 1)) == (
        SMALL_RECORDS,
        SMALL_RECORDS,
    )
    whole = record_span(header, TimeRange(before, after))
    assert whole == (0, SMALL_RECORDS)


# --------------------------------------------------------------------------- #
# referansla bit duzeyinde ayni
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("width_ns", [10_000_000, 100_000_000, 1_000_000_000])
def test_the_bounded_read_matches_the_reference_decoder(small: Path, width_ns: int) -> None:
    header = _header(small)
    start = header.t0_utc_ns + 2 * RECORD_PERIOD_NS
    window = TimeRange(start, start + width_ns)

    with MappedSource(small) as source:
        buffer = source.data()
        reference = query_acoustic_channel(buffer, 0, window)
        result = bounded_query(buffer, header, 0, window)

    assert np.array_equal(result.timestamps_ns, reference.timestamps_ns)
    assert np.array_equal(result.values, reference.values)
    assert result.timestamps_ns.dtype == np.int64
    assert result.values.dtype == np.float64


def test_every_channel_matches_the_reference(small: Path) -> None:
    header = _header(small)
    start = header.t0_utc_ns + RECORD_PERIOD_NS
    window = TimeRange(start, start + 250_000_000)

    with MappedSource(small) as source:
        buffer = source.data()
        for channel in range(header.channel_count):
            reference = query_acoustic_channel(buffer, channel, window)
            result = bounded_query(buffer, header, channel, window)
            assert np.array_equal(result.values, reference.values), f"kanal {channel}"
            assert np.array_equal(result.timestamps_ns, reference.timestamps_ns)


def test_the_whole_recording_matches_the_reference(small: Path) -> None:
    header = _header(small)
    window = TimeRange(header.t0_utc_ns, header.t0_utc_ns + SMALL_RECORDS * RECORD_PERIOD_NS)

    with MappedSource(small) as source:
        buffer = source.data()
        reference = query_acoustic_channel(buffer, 0, window)
        result = bounded_query(buffer, header, 0, window)

    assert np.array_equal(result.values, reference.values)
    assert result.record_count == SMALL_RECORDS


def test_a_window_outside_the_recording_is_empty(small: Path) -> None:
    header = _header(small)
    far = header.t0_utc_ns + 10_000 * RECORD_PERIOD_NS
    with MappedSource(small) as source:
        result = bounded_query(source.data(), header, 0, TimeRange(far, far + 1_000_000))
    assert result.record_count == 0
    assert result.timestamps_ns.size == 0
    assert result.values.size == 0


def test_an_unknown_channel_is_refused(small: Path) -> None:
    header = _header(small)
    with MappedSource(small) as source, pytest.raises(ValueError, match="Kanal"):
        bounded_query(source.data(), header, header.channel_count, TimeRange(0, 1))


# --------------------------------------------------------------------------- #
# sinirlilik: is dosya boyutundan bagimsiz
# --------------------------------------------------------------------------- #


def test_the_same_window_touches_the_same_records_in_a_ten_times_larger_file(
    small: Path, large: Path
) -> None:
    """Sınırlılığın kanıtı: dosya 10x büyürken okunan kayıt sayısı değişmez."""
    small_header, large_header = _header(small), _header(large)
    assert large_header.record_count == 10 * small_header.record_count

    width = 2 * RECORD_PERIOD_NS
    results: list[int] = []
    for path, header in ((small, small_header), (large, large_header)):
        start = header.t0_utc_ns + 5 * RECORD_PERIOD_NS
        with MappedSource(path) as source:
            result = bounded_query(source.data(), header, 0, TimeRange(start, start + width))
        results.append(result.record_count)

    assert results == [2, 2]


def test_the_bounded_read_returns_the_same_samples_from_either_file(
    small: Path, large: Path
) -> None:
    """Aynı pencere, aynı seed: büyük dosyadan okunan da aynı örnekleri verir."""
    small_header, large_header = _header(small), _header(large)
    start_offset = 5 * RECORD_PERIOD_NS
    width = 2 * RECORD_PERIOD_NS

    with MappedSource(small) as source:
        first = bounded_query(
            source.data(),
            small_header,
            0,
            TimeRange(
                small_header.t0_utc_ns + start_offset, small_header.t0_utc_ns + start_offset + width
            ),
        )
    with MappedSource(large) as source:
        second = bounded_query(
            source.data(),
            large_header,
            0,
            TimeRange(
                large_header.t0_utc_ns + start_offset, large_header.t0_utc_ns + start_offset + width
            ),
        )

    assert np.array_equal(first.values, second.values)
    assert first.record_count == second.record_count == 2
