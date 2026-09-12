"""Profil C yazıcısı ve indeks ölçümü — `F7-035`.

Bir fixture üreticisinin tek gerçek sınavı, **üretim çözücüsünün**
çıktısını okuyabilmesidir. Kendi yazdığını kendi okuyan bir üretici,
ikisi birden yanlışsa bunu asla göstermez. Bu yüzden testler üretilen
klasörü `profile_c.decode_file` ile çözer.

İkinci sınav, yazıcının şemayla ayrışmamasıdır. Yazıcı offsetleri sabit
yazar; şema onları veri olarak taşır. Ayrışırlarsa üretilen bütün
fixture'lar okunamaz hâle gelir ve bu, fark edilmesi güç bir kırılmadır.

Ölçüm tarafında sınanan şey sayı değil **yöntemdir**: çıkarımın hangi
ölçümlerden geldiği ve bütçe kapısının gerçekten durdurup durmadığı.
Sayının kendisi makineye bağlıdır ve teste gömülmez.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from tools.profile_c_writer import (
    FRAME_PERIOD_NS,
    WriteSpec,
    folder_name,
    schema_matches,
    write_recording,
)

from sonar_analyzer.io.decoders.profile_c import (
    check_frame_sequence,
    decode_file,
    measure_drift,
)
from sonar_analyzer.io.decoders.profile_c_folder import Stream, discover
from sonar_analyzer.io.schema.loader import load, load_text
from sonar_analyzer.io.schema.model import Schema

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"
REPORT = ROOT / "docs" / "perf" / "results" / "profile-c-index.json"
DOC = ROOT / "docs" / "perf" / "profile-c-index.md"

SENSORS = 4
SAMPLES = 8


@pytest.fixture(scope="module")
def schema() -> Schema:
    text = EXAMPLE.read_text(encoding="utf-8")
    return load_text(
        text.replace("sensor_count = 32", f"sensor_count = {SENSORS}").replace(
            "frame_samples = 820", f"frame_samples = {SAMPLES}"
        )
    )


@pytest.fixture
def recording(tmp_path: Path) -> Path:
    return write_recording(tmp_path, WriteSpec(seconds=3, sensors=SENSORS, samples=SAMPLES))


# --------------------------------------------------------------------------- #
# URETIM COZUCUSU OKUYABILIYOR
# --------------------------------------------------------------------------- #


def test_the_production_decoder_reads_the_written_files(recording: Path, schema: Schema) -> None:
    """Asıl kabul: kendi yazdığını kendi okuyan üretici bir şey kanıtlamaz."""
    folder = discover(recording)
    first = folder.listing(Stream.RX).files[0]

    decoded = decode_file(schema, first.path.read_bytes())

    assert decoded.frame_count == 10
    assert decoded.issues == ()
    assert decoded.crc_checked is True


def test_every_written_file_decodes(recording: Path, schema: Schema) -> None:
    folder = discover(recording)
    for stream in Stream:
        for item in folder.listing(stream).files:
            decoded = decode_file(schema, item.path.read_bytes())
            assert decoded.frame_count == 10, f"{item.path.name} eksik frame"
            assert decoded.issues == (), f"{item.path.name}: {decoded.issues}"


def test_the_header_crc_is_correct(recording: Path, schema: Schema) -> None:
    """Yazıcı CRC'yi kendi alanı hariç hesaplamalı (`ADR-011`)."""
    folder = discover(recording)
    for item in folder.listing(Stream.RX).files:
        decode_file(schema, item.path.read_bytes())  # CRC tutmazsa yukselir


def test_the_payload_crc_is_correct(recording: Path, schema: Schema) -> None:
    folder = discover(recording)
    decoded = decode_file(schema, folder.listing(Stream.RX).files[0].path.read_bytes())

    assert all(frame.crc_ok for frame in decoded.frames)


# --------------------------------------------------------------------------- #
# YAZICI SEMAYLA AYRISMIYOR
# --------------------------------------------------------------------------- #


def test_the_writer_matches_the_example_schema() -> None:
    """Yazıcı sabit offset yazar, şema onları veri taşır; ayrışmamalılar."""
    assert schema_matches(load(EXAMPLE)) is True


def test_a_changed_header_size_is_detected() -> None:
    """Şema büyürse yazıcı bunu bildirmeli, sessizce yanlış yazmamalı."""
    bigger = load_text(
        EXAMPLE.read_text(encoding="utf-8")
        .replace("[structs.FrameHeader]\nsize = 128", "[structs.FrameHeader]\nsize = 132")
        .replace(
            'name = "platform_raw"\ntype = "uint8_t"\noffset = 72\ncount = 48',
            'name = "platform_raw"\ntype = "uint8_t"\noffset = 72\ncount = 52',
        )
        .replace(
            'name = "payload_crc32"\ntype = "uint32_t"\noffset = 120',
            'name = "payload_crc32"\ntype = "uint32_t"\noffset = 124',
        )
        .replace(
            'name = "header_crc32"\ntype = "uint32_t"\noffset = 124',
            'name = "header_crc32"\ntype = "uint32_t"\noffset = 128',
        )
    )

    assert schema_matches(bigger) is False


# --------------------------------------------------------------------------- #
# KLASOR DUZENI
# --------------------------------------------------------------------------- #


def test_the_folder_name_is_a_utc_stamp(tmp_path: Path) -> None:
    spec = WriteSpec(seconds=1, sensors=SENSORS, samples=SAMPLES)
    folder = write_recording(tmp_path, spec)

    assert folder.name == folder_name(spec)
    assert folder.name.endswith("Z")
    assert ":" not in folder.name


def test_both_streams_are_written(recording: Path) -> None:
    folder = discover(recording)

    assert folder.missing_streams == ()
    assert len(folder.listing(Stream.TX).files) == 3
    assert len(folder.listing(Stream.RX).files) == 3


def test_a_manifest_is_written(recording: Path) -> None:
    folder = discover(recording)

    assert folder.manifest is not None
    assert folder.manifest["sensor_count"] == SENSORS
    assert folder.manifest["schema_id"] == "sonar-profile-c"


def test_silent_seconds_produce_no_tx_file(tmp_path: Path) -> None:
    """Yayın yapılmayan saniyede Tx dosyası üretilmez (§2.3)."""
    folder = write_recording(
        tmp_path, WriteSpec(seconds=5, sensors=SENSORS, samples=SAMPLES, tx_seconds=(0, 2, 4))
    )
    result = discover(folder)

    assert len(result.listing(Stream.TX).files) == 3
    assert len(result.listing(Stream.RX).files) == 5
    assert result.listing(Stream.TX).gaps == (1, 3)


# --------------------------------------------------------------------------- #
# FRAME ICERIGI
# --------------------------------------------------------------------------- #


def test_frame_indices_continue_across_files(recording: Path, schema: Schema) -> None:
    """İkinci dosyanın ilk frame'i 10'dan başlar; sayaç dosyada sıfırlanmaz."""
    folder = discover(recording)
    files = folder.listing(Stream.RX).files

    second = decode_file(schema, files[1].path.read_bytes())

    assert second.frames[0].index == 10
    assert check_frame_sequence(second, file_index=1) == []


def test_each_frame_carries_different_samples(recording: Path, schema: Schema) -> None:
    """Bütün frame'ler aynı olsaydı bir offset hatası fark edilmezdi."""
    folder = discover(recording)
    decoded = decode_file(schema, folder.listing(Stream.RX).files[0].path.read_bytes())

    assert not np.array_equal(decoded.frames[0].samples, decoded.frames[1].samples)


def test_the_frame_period_is_not_one_hundred_milliseconds(recording: Path, schema: Schema) -> None:
    """Asıl kabul: 820/8192 = 100,0977 ms; yazıcı 100 ms yazmamalı (`D-27`)."""
    assert FRAME_PERIOD_NS == 100_097_656

    folder = discover(recording)
    decoded = decode_file(schema, folder.listing(Stream.RX).files[0].path.read_bytes())
    step = decoded.frames[1].timestamp_ns - decoded.frames[0].timestamp_ns

    assert step == FRAME_PERIOD_NS
    assert step != 100_000_000


def test_the_written_drift_is_zero_against_the_nominal_period(
    recording: Path, schema: Schema
) -> None:
    """Yazıcı nominal ızgaraya yazıyorsa sapma sıfır çıkmalı."""
    folder = discover(recording)
    decoded = decode_file(schema, folder.listing(Stream.RX).files[0].path.read_bytes())

    drift = measure_drift(decoded, 8192.0, 820)

    assert drift.measurable is True
    assert abs(drift.ppm) < 1.0


def test_the_tx_stream_marks_transmission(recording: Path, schema: Schema) -> None:
    folder = discover(recording)
    tx = decode_file(schema, folder.listing(Stream.TX).files[0].path.read_bytes())
    rx = decode_file(schema, folder.listing(Stream.RX).files[0].path.read_bytes())

    assert tx.frames[0].flags["tx_active"] == 1
    assert rx.frames[0].flags["tx_active"] == 0


# --------------------------------------------------------------------------- #
# DETERMINIZM
# --------------------------------------------------------------------------- #


def test_the_same_spec_produces_the_same_bytes(tmp_path: Path) -> None:
    """Tekrar üretilemeyen bir fixture ile hata ayıklamak, hatayı iki kez aramaktır."""
    spec = WriteSpec(seconds=2, sensors=SENSORS, samples=SAMPLES)
    first = write_recording(tmp_path / "a", spec)
    second = write_recording(tmp_path / "b", spec)

    left = (first / "Rx" / "RxData00000.bin").read_bytes()
    right = (second / "Rx" / "RxData00000.bin").read_bytes()

    assert left == right


def test_an_invalid_spec_is_rejected() -> None:
    with pytest.raises(ValueError, match="saniye"):
        WriteSpec(seconds=0)
    with pytest.raises(ValueError, match="pozitif"):
        WriteSpec(sensors=0)


# --------------------------------------------------------------------------- #
# INDEKS OLCUMU — F7-035
# --------------------------------------------------------------------------- #


def test_the_benchmark_report_exists() -> None:
    assert REPORT.is_file(), "olcum raporu uretilmemis"


def test_the_report_records_the_ceiling_and_the_budget() -> None:
    raw = json.loads(REPORT.read_text(encoding="utf-8"))

    assert raw["ceiling_files"] == 1200
    assert raw["open_budget_s"] == 3.0


def test_the_projection_states_its_basis() -> None:
    """Çıkarımın hangi ölçümlerden geldiği yazılmazsa sayı doğrulanamaz."""
    projection = json.loads(REPORT.read_text(encoding="utf-8"))["projection"]

    assert "tarama" in projection["basis"]
    assert "okuma" in projection["basis"]
    assert "caveat" in projection


def test_the_projection_is_arithmetically_consistent() -> None:
    """Çıkarım, raporlanan iki ölçümden türetilebilmeli."""
    raw = json.loads(REPORT.read_text(encoding="utf-8"))
    expected = (
        raw["small"]["scan_per_file_ms"] * raw["ceiling_files"]
        + raw["full"]["read_per_file_ms"] * raw["ceiling_files"]
    ) / 1000

    assert abs(raw["projection"]["projected_s"] - expected) < 0.01


def test_the_measurement_fits_the_open_budget() -> None:
    """Asıl kabul: 1.200 dosyalık kayıt açılış bütçesini aşmamalı."""
    raw = json.loads(REPORT.read_text(encoding="utf-8"))

    assert raw["projection"]["within_budget"] is True
    assert raw["projection"]["projected_s"] <= raw["open_budget_s"]


def test_the_document_records_the_warm_cache_limit() -> None:
    """Ölçümün sınırı yazılmazsa, en iyi durum tek durum sanılır."""
    prose = " ".join(DOC.read_text(encoding="utf-8").split())

    assert "önbellek sıcak" in prose
    assert "en iyi durumdur" in prose
    assert "E-11" in prose


def test_the_document_draws_the_right_conclusion() -> None:
    """Darboğaz veri hacmi değil dosya başına sabit maliyet."""
    prose = " ".join(DOC.read_text(encoding="utf-8").split())

    assert "dosya başına sabit maliyet" in prose
    assert "yavaşlatır" in prose
