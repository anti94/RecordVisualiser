"""Kalite bayrakları dışa aktarmada ve paket denetiminde — `F6-035`.

Kabul: **CRC/gap işaretli örnekler CSV'de ve `--bin-check` özetinde
görünür.**

Bu iş, `F6-030` kabul turunun düşen adımından (`M-05`) doğdu: bozuk
CRC'li bir kayıttan alınan CSV, bozuk örneği hiçbir işaret olmadan
yazıyordu. Okuma katmanı doğru çalışıyordu — kayıp, bilgiyi kullanıcıya
taşıyan yoldaydı.

Testler elle hesaplanmış maskeler ve **gerçek bozuk fixture** ile
çalışır: `crc_error.bin` bilinen tek bir bozuk kayıt taşır, bu yüzden
"1/8 işaretli" beklentisi tahmin değil, bilinen bir sayıdır.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk, Quality
from sonar_analyzer.export.csv_export import (
    DATA_COLUMNS,
    DATA_COLUMNS_WITH_QUALITY,
    QUALITY_OK,
    describe_quality,
    summarize_quality,
    write_channel_csv,
)

ROOT = Path(__file__).resolve().parents[2]
CRC_FIXTURE = ROOT / "tests" / "fixtures" / "crc_error.bin"
GAP_FIXTURE = ROOT / "tests" / "fixtures" / "gap_missing_record.bin"


def _channel() -> ChannelMetadata:
    return ChannelMetadata(
        id="ch0",
        name="Pressure",
        path="Sensors/Pressure",
        unit="bar",
        dtype="float32",
        source=ChannelSource.SENSORS,
        sample_rate_hz=8.0,
    )


def _chunk(quality: list[int] | None) -> DataChunk:
    count = 4
    return DataChunk(
        channel_id="ch0",
        timestamps_ns=np.arange(count, dtype=np.int64) * 125_000_000,
        values=np.arange(count, dtype=np.float64),
        quality=None if quality is None else np.asarray(quality, dtype=np.uint8),
    )


# --------------------------------------------------------------------------- #
# BAYRAK ADLANDIRMASI
# --------------------------------------------------------------------------- #


def test_no_flags_reads_as_ok() -> None:
    assert describe_quality(0) == QUALITY_OK


def test_a_single_flag_is_named_not_numbered() -> None:
    """`2` kimseye bir şey söylemez; `CRC_ERROR` söyler."""
    assert describe_quality(int(Quality.CRC_ERROR)) == "CRC_ERROR"
    assert describe_quality(int(Quality.GAP_BEFORE)) == "GAP_BEFORE"


def test_combined_flags_are_all_listed() -> None:
    mask = int(Quality.CRC_ERROR | Quality.GAP_BEFORE)
    assert describe_quality(mask) == "GAP_BEFORE|CRC_ERROR"


def test_every_defined_flag_has_a_name() -> None:
    """Tanımlı bir bayrağın adsız kalması, onu okunamaz yapardı."""
    for flag in Quality:
        if flag is Quality.OK:
            continue
        assert describe_quality(int(flag)) == flag.name


def test_an_unknown_bit_is_reported_not_dropped() -> None:
    """Sessizce kaybolan bir bayrak, hiç olmayan bir bayraktan kötüdür."""
    unknown = 1 << 6  # Quality'de tanimli degil
    assert describe_quality(unknown) == "BIT_6"
    assert describe_quality(unknown | int(Quality.CRC_ERROR)) == "CRC_ERROR|BIT_6"


# --------------------------------------------------------------------------- #
# CSV SUTUNU
# --------------------------------------------------------------------------- #


def test_a_chunk_without_quality_keeps_the_original_columns(tmp_path: Path) -> None:
    """Bayrak yokken "OK" yazmak, bilmediğimizi biliyormuş gibi göstermek olurdu."""
    result = write_channel_csv(_chunk(None), _channel(), tmp_path / "a.csv")

    assert result.column_names == DATA_COLUMNS
    header = _header(tmp_path / "a.csv")
    assert "quality" not in header


def test_a_chunk_with_quality_gains_the_column(tmp_path: Path) -> None:
    result = write_channel_csv(_chunk([0, 0, 0, 0]), _channel(), tmp_path / "b.csv")

    assert result.column_names == DATA_COLUMNS_WITH_QUALITY
    assert _header(tmp_path / "b.csv").endswith("quality")


def test_the_flagged_sample_is_marked_in_its_own_row(tmp_path: Path) -> None:
    """Asıl kabul: bozuk örnek diğerlerinden ayırt edilebilmeli."""
    quality = [0, int(Quality.CRC_ERROR), 0, int(Quality.GAP_BEFORE)]
    write_channel_csv(_chunk(quality), _channel(), tmp_path / "c.csv")

    rows = _data_rows(tmp_path / "c.csv")
    assert [row[-1] for row in rows] == ["OK", "CRC_ERROR", "OK", "GAP_BEFORE"]


def test_the_value_column_is_unchanged_by_the_new_column(tmp_path: Path) -> None:
    """Sütun eklemek değerleri kaydırmamalı."""
    write_channel_csv(_chunk([0, 2, 0, 1]), _channel(), tmp_path / "d.csv")
    rows = _data_rows(tmp_path / "d.csv")
    assert [row[2] for row in rows] == ["0.0", "1.0", "2.0", "3.0"]
    assert [len(row) for row in rows] == [4, 4, 4, 4]


# --------------------------------------------------------------------------- #
# METADATA OZETI
# --------------------------------------------------------------------------- #


def test_the_summary_says_when_there_is_no_information() -> None:
    assert summarize_quality(_chunk(None)) == "quality_flags=yok (kaynak kalite bilgisi vermedi)"


def test_the_summary_says_zero_flagged_when_all_clean() -> None:
    assert summarize_quality(_chunk([0, 0, 0, 0])) == "quality_flags=var, isaretli=0/4"


def test_the_summary_counts_each_flag(tmp_path: Path) -> None:
    quality = [int(Quality.CRC_ERROR), int(Quality.CRC_ERROR), int(Quality.GAP_BEFORE), 0]
    summary = summarize_quality(_chunk(quality))
    assert "isaretli=3/4" in summary
    assert "CRC_ERROR=2" in summary
    assert "GAP_BEFORE=1" in summary


def test_the_summary_reaches_the_written_file(tmp_path: Path) -> None:
    path = tmp_path / "e.csv"
    write_channel_csv(_chunk([int(Quality.CRC_ERROR), 0, 0, 0]), _channel(), path)
    text = path.read_text(encoding="utf-8")
    assert "# quality_flags=var, isaretli=1/4 (CRC_ERROR=1)" in text


# --------------------------------------------------------------------------- #
# GERCEK BOZUK FIXTURE ile UCTAN UCA
# --------------------------------------------------------------------------- #


def test_the_corrupt_fixture_exports_with_its_flag_visible(tmp_path: Path) -> None:
    """`M-05`'in düştüğü yer: bozuk kayıt artık CSV'de görünmeli."""
    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    repository = FileRecordingRepository()
    repository.open(CRC_FIXTURE, cache_path=tmp_path / "index.sidx")
    metadata = repository.metadata()
    channel = next(iter(repository.channels()))
    chunk = repository.query(channel.id, metadata.time_range)

    assert chunk.quality is not None
    flagged = [int(value) for value in chunk.quality.tolist() if int(value)]
    assert len(flagged) == 1, "fixture tek bozuk kayit tasir"
    assert flagged[0] & int(Quality.CRC_ERROR)

    path = tmp_path / "export.csv"
    write_channel_csv(chunk, channel, path, recording=metadata)

    text = path.read_text(encoding="utf-8")
    assert "CRC_ERROR" in text
    assert "isaretli=1/8" in text


def test_a_healthy_fixture_is_not_falsely_flagged(tmp_path: Path) -> None:
    """Karşı yön: sağlam dosyada bayrak çıkarsa uyarı anlamsızlaşır."""
    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    repository = FileRecordingRepository()
    repository.open(
        ROOT / "tests" / "fixtures" / "valid_8records_v2.bin", cache_path=tmp_path / "i"
    )
    metadata = repository.metadata()
    channel = next(iter(repository.channels()))
    chunk = repository.query(channel.id, metadata.time_range)

    path = tmp_path / "clean.csv"
    write_channel_csv(chunk, channel, path)

    assert "CRC_ERROR" not in path.read_text(encoding="utf-8")


def test_the_gap_fixture_marks_the_sample_after_the_gap(tmp_path: Path) -> None:
    """Boşluk bir bozulma değil, ama görünmez de olmamalı."""
    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    repository = FileRecordingRepository()
    repository.open(GAP_FIXTURE, cache_path=tmp_path / "g.sidx")
    metadata = repository.metadata()
    channel = next(iter(repository.channels()))
    chunk = repository.query(channel.id, metadata.time_range)

    path = tmp_path / "gap.csv"
    write_channel_csv(chunk, channel, path)

    assert "GAP_BEFORE" in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# PAKET DENETIMI OZETI
# --------------------------------------------------------------------------- #


def test_bin_check_reports_the_flag_for_the_corrupt_fixture(tmp_path: Path) -> None:
    """`--bin-check`, bilinen bozuk dosyada sessiz kalmamalı."""
    from sonar_analyzer.application.bin_check import run_bin_check

    report = run_bin_check(CRC_FIXTURE, tmp_path / "out")
    joined = "\n".join(report.lines)

    assert "kalite:" in joined
    assert "CRC_ERROR=1" in joined
    assert "1/8 ornek isaretli" in joined


def test_bin_check_says_clean_when_nothing_is_flagged(tmp_path: Path) -> None:
    from sonar_analyzer.application.bin_check import run_bin_check

    report = run_bin_check(ROOT / "tests" / "fixtures" / "valid_8records_v2.bin", tmp_path / "ok")
    joined = "\n".join(report.lines)

    assert "hicbirinde bayrak yok" in joined
    assert "CRC_ERROR" not in joined


# --------------------------------------------------------------------------- #
# YARDIMCILAR
# --------------------------------------------------------------------------- #


def _header(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            return line
    raise AssertionError("baslik satiri yok")


def _data_rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    header_seen = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if not header_seen:
            header_seen = True
            continue
        rows.append(line.split(","))
    return rows
