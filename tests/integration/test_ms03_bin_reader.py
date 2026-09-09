"""Faz 2 milestone kabul koşusu — `F2-041`, `ms/03-bin-reader`.

Faz kabul ölçütü (plan Bölüm 22.3): *"Örnek dosya güvenilir çözümlenmeli;
kanal, olay ve zaman sorguları referans değerlerle eşleşmeli."*

`F2-041` kabul kontrolü: **geçerli, bozuk, CRC'li, çoklu dosya ve sorgu**
kontrolleri geçer. Bu dosya o beş başlığın her biri için tutanağa
(`docs/release/ms-03-bin-reader.md` §3) dayanak olan koşuyu yapar; ayrıntılı
alan-alan doğrulama ilgili işlerin kendi testlerindedir (`F2-017`, `F2-018`,
`F2-039`, `F2-040`).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.domain.event import Severity
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.decoders.errors import FormatError
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.repository.protocol import EventFilter, RecordingRepository
from sonar_analyzer.repository.recording_collection import RecordingCollection

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
START_TIME_UTC_NS = 1_788_901_200_000_000_000


def _copy(tmp_path: Path, filename: str, new_name: str | None = None) -> Path:
    target = tmp_path / (new_name or filename)
    shutil.copyfile(FIXTURES_DIR / filename, target)
    return target


# -- 1. GECERLI: ornek dosya guvenilir cozumlenir --------------------------


def test_valid_file_is_decoded_reliably(tmp_path: Path) -> None:
    """Kabul başlığı 1/5: geçerli dosya kontrolleri."""
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "valid_8records.bin"))
        metadata = repository.metadata()

        assert metadata.record_count == 8
        assert metadata.channel_count == 8
        assert metadata.file_size_bytes == 544
        assert metadata.format_version == 1
        assert metadata.time_range.start_ns == START_TIME_UTC_NS
        assert metadata.time_range.duration_ns == 1_000_000_000
        assert len(repository.channels()) == 8
        # Hicbir kayit kalite bayragi tasimaz: bosluk, jitter, CRC hatasi yok.
        chunk = repository.query("ch0", metadata.time_range)
        for flag in (Quality.GAP_BEFORE, Quality.CRC_ERROR, Quality.JITTER, Quality.SUSPECT):
            assert not chunk.has_flag(flag)


def test_file_repository_satisfies_the_repository_protocol(tmp_path: Path) -> None:
    """Faz 1'de tanımlanan sözleşme (F1-016) gerçek dosya okuyucusuyla da karşılanır."""
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "valid_8records.bin"))
        assert isinstance(repository, RecordingRepository)


# -- 2. BOZUK: K-01..K-06 beklenen sonucu uretir ---------------------------


@pytest.mark.parametrize(
    ("filename", "expected_record_count"),
    [
        ("truncated_last_record.bin", 7),  # K-02: son kayit yarim, 7 tam kayit
        ("gap_missing_record.bin", 8),  # K-03: sequence_no 5 yok
        ("name_index_mismatch.bin", 8),  # K-06: ad uyumsuz, kayit atilmaz
    ],
)
def test_corrupt_but_openable_files_keep_intact_records(
    tmp_path: Path, filename: str, expected_record_count: int
) -> None:
    """Kabul başlığı 2/5: bozuk dosya kontrolleri — fail-soft davranış."""
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, filename))
        metadata = repository.metadata()

        assert metadata.record_count == expected_record_count
        # Saglam kayitlar eksiksiz okunur ve teshis kaybolmaz.
        chunk = repository.query("ch0", metadata.time_range)
        assert len(chunk.values) == expected_record_count


@pytest.mark.parametrize("filename", ["truncated_header.bin", "unsupported_version.bin"])
def test_unopenable_files_are_rejected_with_a_typed_error(tmp_path: Path, filename: str) -> None:
    """K-01 ve K-05 dosyayı açmayı reddeder; genel 'bozuk dosya' hatası verilmez."""
    with FileRecordingRepository() as repository, pytest.raises(FormatError):
        repository.open(_copy(tmp_path, filename))


def test_gap_is_reported_as_a_quality_flag_and_not_interpolated(tmp_path: Path) -> None:
    """K-03: kayıp periyot uydurma değerle doldurulmaz, bayrakla gösterilir."""
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "gap_missing_record.bin"))
        chunk = repository.query("ch0", repository.metadata().time_range)

        assert len(chunk.values) == 8  # 8 fiziksel kayit, uydurma 9. deger yok
        assert chunk.has_flag(Quality.GAP_BEFORE)


# -- 3. CRC'LI: v2 dosyasi ve tek bayt bozulmasi ---------------------------


def test_crc_capable_file_opens_and_reports_no_error_when_intact(tmp_path: Path) -> None:
    """Kabul başlığı 3/5: CRC'li dosya kontrolleri — sağlam v2."""
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "valid_8records_v2.bin"))
        metadata = repository.metadata()

        assert metadata.format_version == 2
        assert metadata.file_size_bytes == 580
        assert metadata.record_count == 8
        chunk = repository.query("ch0", metadata.time_range)
        assert not chunk.has_flag(Quality.CRC_ERROR)


def test_single_byte_corruption_is_flagged_without_losing_other_records(
    tmp_path: Path,
) -> None:
    """K-04: tek bayt bozulması yalnız o kaydı işaretler, diğer 7'si okunur."""
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "crc_error.bin"))
        span = repository.metadata().time_range
        chunk = repository.query("ch0", span)

        crc_errors = chunk.flagged_indices(Quality.CRC_ERROR).tolist()
        assert crc_errors == [3]  # yalniz Data00003
        # Bozuk kaydin verisi cizilmez (NaN), digerleri saglam.
        values = chunk.values.tolist()
        assert values[3] != values[3]  # NaN
        assert all(value == value for i, value in enumerate(values) if i != 3)

        crc_events = [e for e in repository.events(span) if e.category == "crc_error"]
        assert len(crc_events) == 1
        assert crc_events[0].severity is Severity.ERROR
        assert crc_events[0].source_offset == 36 + 3 * 68


# -- 4. COKLU DOSYA: kimlikler cakismaz ------------------------------------


def test_multiple_recordings_keep_separate_identities(tmp_path: Path) -> None:
    """Kabul başlığı 4/5: çoklu dosya kontrolleri."""
    first = _copy(tmp_path, "valid_8records.bin", "kayit-a.bin")
    second = _copy(tmp_path, "gap_missing_record.bin", "kayit-b.bin")

    collection = RecordingCollection()
    try:
        first_id = collection.open(first)
        second_id = collection.open(second)

        assert first_id != second_id
        assert len(collection.recordings()) == 2

        channel_ids = [channel.id for channel in collection.channels()]
        assert len(channel_ids) == 16
        assert len(set(channel_ids)) == 16  # kanal kimlikleri cakismaz
        assert all(":" in channel_id for channel_id in channel_ids)

        span = TimeRange(START_TIME_UTC_NS, START_TIME_UTC_NS + 1_000_000_000)
        chunk = collection.query(f"{first_id}:ch0", span)
        assert chunk.channel_id == f"{first_id}:ch0"
        assert len(chunk.values) == 8

        # Olaylar hangi kayittan geldigi bilgisini korur.
        events = collection.events(span)
        assert {item.recording_id for item in events} == {first_id, second_id}
    finally:
        collection.close_all()
    assert collection.recordings() == ()


# -- 5. SORGU: zaman araligi ve olay filtreleri ---------------------------


def test_time_range_queries_respect_boundaries(tmp_path: Path) -> None:
    """Kabul başlığı 5/5: sorgu kontrolleri — [başlangıç, bitiş) sınırları."""
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "valid_8records.bin"))
        period = 125_000_000

        # Tek kayitlik pencere: yalniz ilk kayit.
        single = repository.query("ch0", TimeRange(START_TIME_UTC_NS, START_TIME_UTC_NS + period))
        assert len(single.values) == 1
        assert single.timestamps_ns.tolist() == [START_TIME_UTC_NS]

        # Yarim pencere: ilk dort kayit.
        half = repository.query("ch0", TimeRange(START_TIME_UTC_NS, START_TIME_UTC_NS + 4 * period))
        assert len(half.values) == 4

        # Kayit araliginin tamamen disi: bos ama gecerli sonuc.
        outside = repository.query(
            "ch0",
            TimeRange(START_TIME_UTC_NS + 10 * period, START_TIME_UTC_NS + 12 * period),
        )
        assert len(outside.values) == 0
        assert outside.channel_id == "ch0"


def test_max_points_budget_limits_returned_samples(tmp_path: Path) -> None:
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "valid_8records.bin"))
        span = repository.metadata().time_range

        chunk = repository.query("ch0", span, max_points=4)
        assert len(chunk.values) <= 4
        # DataChunk.__post_init__ zaman/deger/kalite uzunluklarinin esitligini
        # zaten dogruluyor; burada butcenin uygulandigi ve parcanin gecerli
        # kaldigi kontrol edilir.
        assert len(chunk) == len(chunk.values)
        assert chunk.quality is not None
        assert len(chunk.quality) == len(chunk.values)


def test_event_filters_return_only_matching_events(tmp_path: Path) -> None:
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "valid_8records.bin"))
        span = repository.metadata().time_range

        all_events = repository.events(span)
        assert len(all_events) > 0

        bit_only = repository.events(span, EventFilter(sources=["BIT"]))
        assert bit_only
        assert all(event.source == "BIT" for event in bit_only)

        errors_only = repository.events(span, EventFilter(min_severity=Severity.ERROR))
        assert all(event.severity.rank >= Severity.ERROR.rank for event in errors_only)

        assert repository.events(span, EventFilter(sources=["OLMAYAN"])) == ()


def test_unknown_channel_query_is_rejected(tmp_path: Path) -> None:
    with FileRecordingRepository() as repository:
        repository.open(_copy(tmp_path, "valid_8records.bin"))
        with pytest.raises(KeyError):
            repository.query("olmayan-kanal", repository.metadata().time_range)
