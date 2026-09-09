"""Bağımsız golden sonuçlarını parser ile karşılaştırma — `F2-039`.

Kabul: kanal, örnek, olay, zaman ve CRC sonuçları referansla eşleşir.

Buradaki **tüm** beklenen değerler `docs/format/fixture-valid-8records.md`
(`F0-009` çıktısı) ve `docs/format/channel-map.md` §2'den elle
aktarılmıştır — parser çıktısından türetilmemiştir. Referans, parser
yazılmadan **önce** sabitlendi; bu yüzden test iki bağımsız kaynağın
(belge ve kod) birbirini doğrulaması anlamına gelir. Kaynak dosya da
üreticiden değil, commit'lenmiş `tests/fixtures/valid_8records.bin`
baytlarından okunur.

Belge "float32 dönüşümü kayıpsızdır; karşılaştırmalar tolerans kullanmadan
`==` ile yapılabilir" der (§1) — testler bu yüzden tolerans kullanmaz.
"""

from __future__ import annotations

import hashlib
import zlib
from collections.abc import Iterator
from pathlib import Path

import pytest

from sonar_analyzer.domain.event import BitState, Severity
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TxState
from sonar_analyzer.io.decoders.crc_validation import is_crc_validated
from sonar_analyzer.repository.file_repository import FileRecordingRepository

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"

# -- docs/format/fixture-valid-8records.md §2: beklenen header ---------------
START_TIME_UTC_NS = 1_788_901_200_000_000_000  # 2026-09-08T21:00:00.000Z
EXPECTED_VERSION = 1
EXPECTED_PERIOD_US = 125_000
EXPECTED_CHANNEL_COUNT = 8

# -- §4: dosya duzeyi beklentiler -------------------------------------------
EXPECTED_FILE_SIZE = 544
EXPECTED_RECORD_COUNT = 8
EXPECTED_WINDOW_TOTAL_MS = 1_000
EXPECTED_SHA256 = "5094b9b0bc585518cf7fa9dc372d3e997f32b59caeb156cb4c0f9ab9d039fce9"
EXPECTED_FILE_CRC32 = 0x7314EC15

# -- §3: beklenen kayitlar (n, elapsed_us, offset, CH0, CH2, CH3, CH5, CH6) --
EXPECTED_RECORDS = (
    (0, 0, 32, 100.0, 0.0, 0.0, 2.5, 10.0),
    (1, 125_000, 96, 100.5, 0.125, -0.125, -2.5, 10.25),
    (2, 250_000, 160, 101.0, 0.25, -0.25, 2.5, 10.5),
    (3, 375_000, 224, 101.5, 0.375, -0.375, -2.5, 10.75),
    (4, 500_000, 288, 102.0, 0.5, -0.5, 2.5, 11.0),
    (5, 625_000, 352, 102.5, 0.625, -0.625, -2.5, 11.25),
    (6, 750_000, 416, 103.0, 0.75, -0.75, 2.5, 11.5),
    (7, 875_000, 480, 103.5, 0.875, -0.875, -2.5, 11.75),
)
#: §3: "CH1 = 25.0, CH4 = 1.0, CH7 = 48.0 tum kayitlarda sabittir."
EXPECTED_CONSTANT_CHANNELS = {"ch1": 25.0, "ch4": 1.0, "ch7": 48.0}

# -- docs/format/channel-map.md §2: minimal sozluk (CH0-CH7) ----------------
EXPECTED_CHANNEL_PATHS = (
    "Sensors/Pressure",
    "Sensors/Temperature",
    "Sensors/Accelerometer/X",
    "Sensors/Accelerometer/Y",
    "Sensors/Accelerometer/Z",
    "Acoustic/Hydrophone 1",
    "Navigation/Depth",
    "Vehicle/Voltage",
)
EXPECTED_CHANNEL_UNITS = ("bar", "°C", "g", "g", "g", "Pa", "m", "V")
#: §5: "her biri 8 ornek, ornekleme 8 Hz".
EXPECTED_SAMPLE_RATE_HZ = 8.0

# -- §5: turetilmis beklentiler --------------------------------------------
EXPECTED_BIT_FAIL_AT_MS = 500
EXPECTED_BIT_FAIL_BIT = 8
EXPECTED_TX_START_MS = 250
EXPECTED_TX_STOP_MS = 750
EXPECTED_TX_DURATION_MS = 500
EXPECTED_TX_UNCERTAINTY_NS = 125_000_000


@pytest.fixture()
def repository() -> Iterator[FileRecordingRepository]:
    repo = FileRecordingRepository()
    with repo:
        repo.open(FIXTURE_PATH)
        yield repo


def _span(repo: FileRecordingRepository) -> TimeRange:
    return repo.metadata().time_range


# -- ZAMAN: header ankoru, kayit zamanlari ve kapsanan aralik ---------------


def test_time_anchor_and_covered_span_match_reference(
    repository: FileRecordingRepository,
) -> None:
    """§2 + §4: baslangic 21:00:00.000Z, kapsanan pencere toplami 1000 ms."""
    metadata = repository.metadata()

    assert metadata.time_range.start_ns == START_TIME_UTC_NS
    assert metadata.time_range.end_ns == START_TIME_UTC_NS + EXPECTED_WINDOW_TOTAL_MS * 1_000_000
    assert metadata.record_period_ns == EXPECTED_PERIOD_US * 1_000
    assert metadata.format_version == EXPECTED_VERSION
    assert metadata.record_count == EXPECTED_RECORD_COUNT
    assert metadata.channel_count == EXPECTED_CHANNEL_COUNT
    assert metadata.file_size_bytes == EXPECTED_FILE_SIZE


def test_each_record_timestamp_matches_documented_elapsed_us(
    repository: FileRecordingRepository,
) -> None:
    """§3 'elapsed_us' ve 'UTC' sutunlari: 0-875 ms, 125 ms adimlarla."""
    chunk = repository.query("ch0", _span(repository))

    assert len(chunk.timestamps_ns) == EXPECTED_RECORD_COUNT
    for (_n, elapsed_us, _offset, *_values), actual_ns in zip(
        EXPECTED_RECORDS, chunk.timestamps_ns.tolist()
    ):
        assert actual_ns == START_TIME_UTC_NS + elapsed_us * 1_000


# -- KANAL: yollar, birimler, ornekleme hizi ve ornek sayisi ---------------


def test_channel_list_matches_documented_dictionary(
    repository: FileRecordingRepository,
) -> None:
    """channel-map.md §2: CH0-CH7 yollari ve birimleri."""
    channels = repository.channels()

    assert len(channels) == EXPECTED_CHANNEL_COUNT
    assert tuple(channel.path for channel in channels) == EXPECTED_CHANNEL_PATHS
    assert tuple(channel.unit for channel in channels) == EXPECTED_CHANNEL_UNITS


def test_every_channel_reports_eight_samples_at_eight_hertz(
    repository: FileRecordingRepository,
) -> None:
    """§5: 'her biri 8 ornek, ornekleme 8 Hz'."""
    span = _span(repository)
    for channel in repository.channels():
        assert channel.sample_rate_hz == EXPECTED_SAMPLE_RATE_HZ
        assert len(repository.query(channel.id, span).values) == EXPECTED_RECORD_COUNT


# -- ORNEK: §3 tablosundaki her sayisal deger -------------------------------


@pytest.mark.parametrize("channel_slot", [0, 2, 3, 5, 6])
def test_documented_sample_values_match_exactly(
    repository: FileRecordingRepository, channel_slot: int
) -> None:
    """§3'teki CH0/CH2/CH3/CH5/CH6 sutunlari — tolerans yok (§1)."""
    # EXPECTED_RECORDS demetinde deger sutunlari 3. indeksten baslar.
    column = {0: 3, 2: 4, 3: 5, 5: 6, 6: 7}[channel_slot]
    expected = [row[column] for row in EXPECTED_RECORDS]

    chunk = repository.query(f"ch{channel_slot}", _span(repository))

    assert chunk.values.tolist() == expected


def test_documented_constant_channels_match_exactly(
    repository: FileRecordingRepository,
) -> None:
    """§3: CH1 = 25.0, CH4 = 1.0, CH7 = 48.0 tum kayitlarda sabit."""
    span = _span(repository)
    for channel_id, expected_value in EXPECTED_CONSTANT_CHANNELS.items():
        values = repository.query(channel_id, span).values.tolist()
        assert values == [expected_value] * EXPECTED_RECORD_COUNT


def test_ch3_first_sample_is_positive_zero_not_negative_zero(
    repository: FileRecordingRepository,
) -> None:
    """§1 uyarisi: n=0 icin CH3 baytlari 00 00 00 00 olmali, 00 00 00 80 degil."""
    first_value = repository.query("ch3", _span(repository)).values[0]
    assert first_value == 0.0
    # -0.0 == 0.0 oldugu icin isaret biti ayrica denetlenir.
    assert not str(float(first_value)).startswith("-")


# -- OLAY: BIT arizasi, TX araligi ve bosluk raporu ------------------------


def test_exactly_one_bit_failure_at_documented_time_and_bit(
    repository: FileRecordingRepository,
) -> None:
    """§5: 'tam 1 adet: t = 500 ms, grup Thermal, bit 8, durum FAIL'."""
    span = _span(repository)
    failures = [result for result in repository.bit_results(span) if result.is_failure]

    assert len(failures) == 1
    failure = failures[0]
    assert failure.timestamp_ns == START_TIME_UTC_NS + EXPECTED_BIT_FAIL_AT_MS * 1_000_000
    assert failure.test_id == EXPECTED_BIT_FAIL_BIT
    assert failure.state is BitState.FAIL
    # Belge grubu kisaca 'Thermal' yazar; katalogdaki tam ad 'Thermal Management'.
    assert failure.component.startswith("Thermal")


def test_exactly_one_bit_fail_event_is_reported(
    repository: FileRecordingRepository,
) -> None:
    """Ayni ariza olay tablosunda da tam bir kez ERROR olarak gorunur."""
    events = repository.events(_span(repository))
    fail_events = [event for event in events if event.severity is Severity.ERROR]

    assert len(fail_events) == 1
    assert fail_events[0].timestamp_ns == START_TIME_UTC_NS + EXPECTED_BIT_FAIL_AT_MS * 1_000_000


def test_exactly_one_transmission_interval_matches_reference(
    repository: FileRecordingRepository,
) -> None:
    """§5: 'tam 1 adet: baslangic 250 ms, bitis 750 ms, sure 500 ms, +/-125 ms'."""
    intervals = repository.transmissions(_span(repository))

    assert len(intervals) == 1
    interval = intervals[0]
    assert interval.start_ns == START_TIME_UTC_NS + EXPECTED_TX_START_MS * 1_000_000
    assert interval.end_ns == START_TIME_UTC_NS + EXPECTED_TX_STOP_MS * 1_000_000
    assert interval.duration_ns == EXPECTED_TX_DURATION_MS * 1_000_000
    assert interval.boundary_uncertainty_ns == EXPECTED_TX_UNCERTAINTY_NS
    assert interval.state is TxState.ACTIVE
    assert interval.closed is True


def test_gap_report_is_empty(repository: FileRecordingRepository) -> None:
    """§4 + §5: 'Sira boslugu: yok (sequence_no 0..7 kesintisiz)', bosluk raporu bos liste."""
    events = repository.events(_span(repository))
    gap_events = [event for event in events if event.category == "sequence_gap"]
    assert gap_events == []


# -- CRC: dosya duzeyi referans degeri ve v1'in butunluk iddiasi ------------


def test_file_level_crc32_and_sha256_match_reference() -> None:
    """§4: SHA-256 ve tum dosyanin CRC-32'si (0x7314EC15)."""
    data = FIXTURE_PATH.read_bytes()

    assert len(data) == EXPECTED_FILE_SIZE
    assert hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    assert zlib.crc32(data) & 0xFFFFFFFF == EXPECTED_FILE_CRC32


def test_version_one_reports_no_crc_error_but_claims_no_integrity(
    repository: FileRecordingRepository,
) -> None:
    """§4: 'CRC hatasi: yok (bu surumde CRC alani yok)' — dogrulanmis da sayilmaz."""
    metadata = repository.metadata()
    events = repository.events(_span(repository))

    assert [event for event in events if event.category == "crc_error"] == []
    assert is_crc_validated(metadata.format_version) is False
    assert any("CRC icermiyor" in message for message in metadata.diagnostics)
