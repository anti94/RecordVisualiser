"""Klasör tabanlı Profil C repository'si — `F7-036`…`F7-044`.

Kabuller: `RecordingRepository` sözleşmesinin yedi metodu da karşılanır;
zaman aralığı klasörden üretilir; Tx/Rx × sensör kanalları sunulur;
sorgu dosya sınırlarını aşar; seyreltme sınırlarda tutarlıdır; önden
okuma bellek bütçesini aşmaz; bozuk ve eksik dosya oynatmada görünür.

Bu katmanın sessiz hatası **dosya sınırıdır**. Üç dosyaya yayılan bir
aralık, sınırda örnek kaybederse ya da tekrarlarsa kimse fark etmez:
grafik yine çizilir, sayılar yine makul görünür. Testlerin çoğunluğu bu
yüzden sınırı geçen sorguları ve örnek sayılarını doğrular.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest
from tools.profile_c_writer import WriteSpec, write_recording

from sonar_analyzer.domain.channel import COMPLEX_DTYPES, ChannelSource
from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.io.schema.loader import load_text
from sonar_analyzer.io.schema.model import Schema
from sonar_analyzer.repository.folder_repository import (
    FolderRecordingRepository,
    channel_id,
    channel_path,
    parse_channel_id,
)
from sonar_analyzer.repository.protocol import RecordingRepository

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"

SENSORS = 4
SAMPLES = 8
FRAMES_PER_FILE = 10


@pytest.fixture(scope="module")
def schema() -> Schema:
    text = EXAMPLE.read_text(encoding="utf-8")
    return load_text(
        text.replace("sensor_count = 32", f"sensor_count = {SENSORS}").replace(
            "frame_samples = 820", f"frame_samples = {SAMPLES}"
        )
    )


@pytest.fixture
def repository(tmp_path: Path, schema: Schema):
    folder = write_recording(tmp_path, WriteSpec(seconds=3, sensors=SENSORS, samples=SAMPLES))
    repo = FolderRecordingRepository()
    repo.open(folder, schema)
    yield repo
    repo.close()


# --------------------------------------------------------------------------- #
# F7-036 — SOZLESME
# --------------------------------------------------------------------------- #


def test_it_satisfies_the_repository_protocol(repository: FolderRecordingRepository) -> None:
    """Asıl kabul: arayüz klasörle dosya arasındaki farkı görmemeli."""
    assert isinstance(repository, RecordingRepository)


def test_every_contract_method_is_callable(repository: FolderRecordingRepository) -> None:
    span = repository.metadata().time_range

    assert repository.channels()
    assert repository.query(channel_id_value="rx-s00", time_range=span) is not None
    assert repository.events(span) == ()
    assert repository.bit_results(span) == ()
    assert repository.transmissions(span) == ()


def test_using_it_before_open_is_refused() -> None:
    """Açılmamış bir repository sessizce boş dönmemeli."""
    with pytest.raises(ValueError, match="open"):
        FolderRecordingRepository().metadata()


# --------------------------------------------------------------------------- #
# F7-037 — ZAMAN ARALIGI
# --------------------------------------------------------------------------- #


def test_the_time_range_spans_the_whole_recording(
    repository: FolderRecordingRepository,
) -> None:
    span = repository.metadata().time_range
    period = repository.metadata().record_period_ns

    assert span.end_ns - span.start_ns == 3 * FRAMES_PER_FILE * period


def test_the_range_covers_the_last_frame_samples(
    repository: FolderRecordingRepository,
) -> None:
    """Asıl kabul: tam aralık sorgusu **bütün** örnekleri döndürmeli.

    İndeksteki `end_ns` son frame'in başlangıcıdır, sonu değil. Uzatmadan
    sorgulanırsa son frame'in örnekleri dışarıda kalır ve eksik veri
    sessizce eksik görünür, bir hata olarak değil.
    """
    span = repository.metadata().time_range
    chunk = repository.query("rx-s00", span)

    assert len(chunk) == 3 * FRAMES_PER_FILE * SAMPLES


def test_the_frame_period_is_measured_not_assumed(
    repository: FolderRecordingRepository,
) -> None:
    """820/8192 kaynaklı kayma gizlenmemeli (`D-27`)."""
    assert repository.metadata().record_period_ns == 100_097_656


def test_the_metadata_names_the_profile(repository: FolderRecordingRepository) -> None:
    meta = repository.metadata()

    assert meta.format_profile == "C"
    assert meta.record_count == 2 * 3 * FRAMES_PER_FILE


# --------------------------------------------------------------------------- #
# F7-038 — KANALLAR
# --------------------------------------------------------------------------- #


def test_two_streams_times_sensors(repository: FolderRecordingRepository) -> None:
    """Asıl kabul: Tx/Rx × sensör."""
    channels = repository.channels()

    assert len(channels) == 2 * SENSORS


def test_channel_ids_and_paths_follow_the_convention(
    repository: FolderRecordingRepository,
) -> None:
    ids = {channel.id for channel in repository.channels()}
    paths = {channel.path for channel in repository.channels()}

    assert "rx-s00" in ids
    assert "tx-s03" in ids
    assert "Rx/Sensor 00" in paths
    assert "Tx/Sensor 03" in paths


def test_channel_ids_sort_numerically(repository: FolderRecordingRepository) -> None:
    """Sıfır dolgu olmasaydı `s10` `s2`'den önce sıralanırdı."""
    rx = sorted(c.id for c in repository.channels() if c.id.startswith("rx"))

    assert rx == [f"rx-s{i:02d}" for i in range(SENSORS)]


def test_channels_are_complex(repository: FolderRecordingRepository) -> None:
    for channel in repository.channels():
        assert channel.dtype == "complex64"
        assert channel.dtype in COMPLEX_DTYPES
        assert channel.source is ChannelSource.ACOUSTIC


def test_the_unit_is_deliberately_empty(repository: FolderRecordingRepository) -> None:
    """Ham sayılar Volt ya da Pascal değildir (`D-34`, `D-35`).

    Bir birim yazmak uydurma olurdu: ölçekleme sabitleri bilinmiyor.
    """
    for channel in repository.channels():
        assert channel.unit is None


def test_the_sample_rate_is_derived_from_the_real_period(
    repository: FolderRecordingRepository,
) -> None:
    channel = repository.channels()[0]
    period_s = repository.metadata().record_period_ns / 1e9

    assert channel.sample_rate_hz is not None
    assert abs(channel.sample_rate_hz - SAMPLES / period_s) < 0.01


def test_a_missing_stream_produces_no_channels(tmp_path: Path, schema: Schema) -> None:
    """Yayın yapılmayan bir oturumda Tx kanalı sunulmaz."""
    folder = write_recording(
        tmp_path, WriteSpec(seconds=2, sensors=SENSORS, samples=SAMPLES, tx_seconds=())
    )
    repo = FolderRecordingRepository()
    repo.open(folder, schema)

    assert all(channel.id.startswith("rx") for channel in repo.channels())
    assert len(repo.channels()) == SENSORS
    repo.close()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("rx-s00", 0), ("tx-s03", 3), ("rx-s31", 31)],
)
def test_channel_ids_round_trip(value: str, expected: int) -> None:
    parsed = parse_channel_id(value)

    assert parsed is not None
    assert parsed[1] == expected
    assert channel_id(parsed[0], parsed[1]) == value
    assert channel_path(parsed[0], parsed[1]).endswith(f"{expected:02d}")


@pytest.mark.parametrize("value", ["", "rx", "rx-s", "xx-s00", "rx-sAB", "rx-s00-extra"])
def test_an_unparseable_channel_id_returns_none(value: str) -> None:
    assert parse_channel_id(value) is None


# --------------------------------------------------------------------------- #
# F7-039 — DOSYA SINIRLARINI ASAN SORGU
# --------------------------------------------------------------------------- #


def test_a_query_spanning_three_files_returns_one_chunk(
    repository: FolderRecordingRepository,
) -> None:
    """Asıl kabul: kullanıcının 1 saniyelik dilimleri bilmesi gerekmez."""
    span = repository.metadata().time_range
    chunk = repository.query("rx-s01", span)

    assert len(chunk) == 3 * FRAMES_PER_FILE * SAMPLES
    assert chunk.channel_id == "rx-s01"


def test_the_timestamps_are_strictly_increasing(
    repository: FolderRecordingRepository,
) -> None:
    """Sınırda sıralama bozulursa kayıt zamanda geri gider."""
    chunk = repository.query("rx-s00", repository.metadata().time_range)

    assert np.all(np.diff(chunk.timestamps_ns) > 0)


def test_no_sample_is_duplicated_at_a_file_boundary(
    repository: FolderRecordingRepository,
) -> None:
    """Sınırda tekrar eden bir örnek, grafikte fark edilmeyen bir hatadır."""
    chunk = repository.query("rx-s00", repository.metadata().time_range)

    assert np.unique(chunk.timestamps_ns).size == chunk.timestamps_ns.size


def test_a_narrow_range_returns_only_what_it_covers(
    repository: FolderRecordingRepository,
) -> None:
    span = repository.metadata().time_range
    period = repository.metadata().record_period_ns
    narrow = TimeRange(start_ns=span.start_ns, end_ns=span.start_ns + period)

    assert len(repository.query("rx-s00", narrow)) == SAMPLES


def test_a_range_outside_the_recording_returns_an_empty_chunk(
    repository: FolderRecordingRepository,
) -> None:
    """Boş ama **geçerli** bir parça dönmeli; hata fırlatılmamalı."""
    span = repository.metadata().time_range
    far = TimeRange(start_ns=span.end_ns + 10**12, end_ns=span.end_ns + 2 * 10**12)

    chunk = repository.query("rx-s00", far)

    assert chunk.is_empty
    assert chunk.values.dtype == np.complex64


def test_an_unknown_channel_returns_an_empty_chunk(
    repository: FolderRecordingRepository,
) -> None:
    chunk = repository.query("hicyok", repository.metadata().time_range)

    assert chunk.is_empty


def test_a_sensor_beyond_the_array_returns_empty(
    repository: FolderRecordingRepository,
) -> None:
    chunk = repository.query("rx-s99", repository.metadata().time_range)

    assert chunk.is_empty


def test_each_sensor_returns_different_data(
    repository: FolderRecordingRepository,
) -> None:
    """Bütün sensörler aynı veriyi verseydi bir indeks hatası gizlenirdi."""
    span = repository.metadata().time_range
    first = repository.query("rx-s00", span).values
    second = repository.query("rx-s01", span).values

    assert not np.array_equal(first, second)


def test_tx_and_rx_are_different_streams(repository: FolderRecordingRepository) -> None:
    span = repository.metadata().time_range

    assert not np.array_equal(
        repository.query("rx-s00", span).values, repository.query("tx-s00", span).values
    )


# --------------------------------------------------------------------------- #
# F7-040 — SEYRELTME
# --------------------------------------------------------------------------- #


def test_decimation_respects_the_point_budget(
    repository: FolderRecordingRepository,
) -> None:
    chunk = repository.query("rx-s00", repository.metadata().time_range, max_points=20)

    assert len(chunk) <= 20


def test_decimation_keeps_the_first_and_last_sample(
    repository: FolderRecordingRepository,
) -> None:
    """Uçları atmak, kaydın başını ve sonunu grafikte kaybettirir."""
    span = repository.metadata().time_range
    full = repository.query("rx-s00", span)
    thin = repository.query("rx-s00", span, max_points=15)

    assert thin.timestamps_ns[0] == full.timestamps_ns[0]
    assert thin.timestamps_ns[-1] == full.timestamps_ns[-1]


def test_decimation_is_even_across_file_boundaries(
    repository: FolderRecordingRepository,
) -> None:
    """Asıl kabul: sınırda örnek yoğunluğu değişmemeli.

    Dosya başına seyreltme yapılsaydı sınırlarda yoğunluk sıçrardı ve
    grafikte görünür bir düzensizlik oluşurdu.
    """
    span = repository.metadata().time_range
    thin = repository.query("rx-s00", span, max_points=30)
    gaps = np.diff(thin.timestamps_ns)

    assert gaps.max() - gaps.min() <= gaps.mean() * 0.5


def test_a_budget_larger_than_the_data_changes_nothing(
    repository: FolderRecordingRepository,
) -> None:
    span = repository.metadata().time_range

    assert len(repository.query("rx-s00", span, max_points=10_000)) == len(
        repository.query("rx-s00", span)
    )


# --------------------------------------------------------------------------- #
# F7-044 — BOZUK VE EKSIK DOSYA
# --------------------------------------------------------------------------- #


def test_a_missing_second_leaves_a_gap_not_a_shift(tmp_path: Path, schema: Schema) -> None:
    """Asıl kabul: eksik saniye zaman ekseninde boşluk olarak kalmalı.

    Sessizce atlansaydı sonraki bütün örnekler 1 saniye öne kayardı ve
    kayıt hiçbir uyarı vermeden yanlış zamanları gösterirdi.
    """
    folder = write_recording(tmp_path, WriteSpec(seconds=3, sensors=SENSORS, samples=SAMPLES))
    (folder / "Rx" / "RxData00001.bin").unlink()

    repo = FolderRecordingRepository()
    repo.open(folder, schema)
    chunk = repo.query("rx-s00", repo.metadata().time_range)

    assert len(chunk) == 2 * FRAMES_PER_FILE * SAMPLES
    gaps = np.diff(chunk.timestamps_ns)
    assert gaps.max() > gaps.min() * 2, "eksik saniye zaman ekseninde gorunmeli"
    repo.close()


def test_a_missing_file_is_reported_as_a_warning(tmp_path: Path, schema: Schema) -> None:
    folder = write_recording(tmp_path, WriteSpec(seconds=3, sensors=SENSORS, samples=SAMPLES))
    (folder / "Rx" / "RxData00001.bin").unlink()

    repo = FolderRecordingRepository()
    repo.open(folder, schema)

    assert any("sayac bosluk" in warning for warning in repo.warnings)
    repo.close()


def test_a_bad_crc_marks_quality_but_keeps_the_data(tmp_path: Path, schema: Schema) -> None:
    """Asıl kabul: bozuk frame işaretlenir, atılmaz."""
    folder = write_recording(tmp_path, WriteSpec(seconds=2, sensors=SENSORS, samples=SAMPLES))
    target = folder / "Rx" / "RxData00000.bin"
    blob = bytearray(target.read_bytes())
    struct.pack_into("<I", blob, 64 + 120, 0xDEADBEEF)
    target.write_bytes(bytes(blob))

    repo = FolderRecordingRepository()
    repo.open(folder, schema)
    chunk = repo.query("rx-s00", repo.metadata().time_range)

    assert len(chunk) == 2 * FRAMES_PER_FILE * SAMPLES, "bozuk frame atilmis"
    assert chunk.quality is not None
    assert int(chunk.quality[0]) == int(Quality.CRC_ERROR)
    assert int(chunk.quality[-1]) == int(Quality.OK)
    repo.close()


def test_a_bad_crc_is_reported_as_a_warning(tmp_path: Path, schema: Schema) -> None:
    folder = write_recording(tmp_path, WriteSpec(seconds=1, sensors=SENSORS, samples=SAMPLES))
    target = folder / "Rx" / "RxData00000.bin"
    blob = bytearray(target.read_bytes())
    struct.pack_into("<I", blob, 64 + 120, 0xDEADBEEF)
    target.write_bytes(bytes(blob))

    repo = FolderRecordingRepository()
    repo.open(folder, schema)

    assert any("CRC_ERROR" in warning for warning in repo.warnings)
    repo.close()


# --------------------------------------------------------------------------- #
# F7-042 — BELLEK BUTCESI
# --------------------------------------------------------------------------- #


def test_the_decoded_cache_is_bounded(tmp_path: Path, schema: Schema) -> None:
    """Asıl kabul: aynı anda bellekte tutulan dosya sayısı sınırlı.

    Sınırsız önbellek 10 dakikalık bir kayıtta 1,17 GiB'i bellekte
    tutardı.
    """
    folder = write_recording(tmp_path, WriteSpec(seconds=12, sensors=SENSORS, samples=SAMPLES))
    repo = FolderRecordingRepository(cache_files=3)
    repo.open(folder, schema)
    repo.query("rx-s00", repo.metadata().time_range)

    assert repo.cached_files <= repo.cache_limit == 3
    repo.close()


def test_closing_releases_the_cache(repository: FolderRecordingRepository) -> None:
    repository.query("rx-s00", repository.metadata().time_range)
    repository.close()

    assert repository.cached_files == 0


# --------------------------------------------------------------------------- #
# ACIK KARARLAR UYDURULMUYOR
# --------------------------------------------------------------------------- #


def test_no_events_are_invented(repository: FolderRecordingRepository) -> None:
    """CIT ve transmisyon blokları opak (`D-30`, `D-31`).

    İçlerinden olay çıkarmak, alan yerleşimini uydurmak olurdu.
    """
    assert repository.events(repository.metadata().time_range) == ()


def test_no_transmission_intervals_are_invented(
    repository: FolderRecordingRepository,
) -> None:
    """PRI ve yayın süresi bilinmeden aralık sınırları çıkarılamaz."""
    assert repository.transmissions(repository.metadata().time_range) == ()
