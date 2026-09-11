"""Sürümlü dosya header yazıcısı — `F5-025`.

Kabul: **dosya format sürümü uygulama sürümünden bağımsız yazılır.**

En güçlü kanıt tur-gidiştir: yazılan başlık, üretim okuyucusuyla
(`F2-*`'nin `read_validated_header`) çözülüp alan alan karşılaştırılır.
İki taraf aynı `struct.Struct` sözleşmesini paylaştığı için ayrışamazlar;
test bunu fiilen doğrular.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sonar_analyzer.io.decoders.crc import header_crc32
from sonar_analyzer.io.decoders.crc_validation import HeaderCrcMismatchError
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_CHANNEL_COUNT,
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_HEADER_SIZE_V2,
    EXPECTED_PERIOD_US,
    EXPECTED_RECORD_SIZE_V1,
    EXPECTED_RECORD_SIZE_V2,
    MAGIC,
)
from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.header_writer import (
    DEFAULT_FORMAT_VERSION,
    build_file_header,
    header_size_for,
    record_size_for,
)

START_NS = 1_788_901_200_000_000_000


# --------------------------------------------------------------------------- #
# yazilan baslik URETIM OKUYUCUSUYLA okunur
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("version", [1, 2])
def test_the_written_header_is_read_back_by_the_production_reader(version: int) -> None:
    raw = build_file_header(start_time_utc_ns=START_NS, version=version)
    header = read_validated_header(raw)

    assert header.magic == MAGIC
    assert header.version == version
    assert header.period_us == EXPECTED_PERIOD_US
    assert header.channel_count == EXPECTED_CHANNEL_COUNT
    assert header.start_time_utc_ns == START_NS


@pytest.mark.parametrize(
    ("version", "header_size", "record_size"),
    [
        (1, EXPECTED_HEADER_SIZE_V1, EXPECTED_RECORD_SIZE_V1),
        (2, EXPECTED_HEADER_SIZE_V2, EXPECTED_RECORD_SIZE_V2),
    ],
)
def test_the_layout_sizes_match_the_reader_constants(
    version: int, header_size: int, record_size: int
) -> None:
    raw = build_file_header(start_time_utc_ns=START_NS, version=version)
    assert len(raw) == header_size
    assert header_size_for(version) == header_size
    assert record_size_for(version) == record_size

    header = read_validated_header(raw)
    assert header.header_size == header_size
    assert header.record_size == record_size


def test_a_written_header_survives_a_real_file_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "kayit.bin"
    target.write_bytes(build_file_header(start_time_utc_ns=START_NS))

    header = read_validated_header(target.read_bytes())
    assert header.start_time_utc_ns == START_NS


# --------------------------------------------------------------------------- #
# FORMAT SURUMU UYGULAMA SURUMUNDEN BAGIMSIZ
# --------------------------------------------------------------------------- #


def test_the_format_version_is_a_small_integer_not_the_app_version() -> None:
    """`VERSION` dosyası `2.25.0` derken başlığa `2` yazılır — ikisi ayrı şey."""
    assert DEFAULT_FORMAT_VERSION in (1, 2)
    header = read_validated_header(build_file_header(start_time_utc_ns=START_NS))
    assert header.version == DEFAULT_FORMAT_VERSION


def test_the_written_version_does_not_change_with_the_app_version() -> None:
    """Uygulama sürümü dosyasını okusak bile başlık sürümü ondan etkilenmez."""
    app_version = Path("VERSION").read_text(encoding="utf-8").strip()
    header = read_validated_header(build_file_header(start_time_utc_ns=START_NS))

    assert app_version not in str(header.version)  # "2.25.0" basliga sizmadi
    assert header.version == DEFAULT_FORMAT_VERSION


def test_the_same_inputs_always_produce_the_same_bytes() -> None:
    """Başlık belirlenimcidir: uygulama sürümü gibi dış bir girdi sızmaz."""
    first = build_file_header(start_time_utc_ns=START_NS)
    second = build_file_header(start_time_utc_ns=START_NS)
    assert first == second


@pytest.mark.parametrize("version", [0, 3, -1, 99])
def test_an_unsupported_format_version_is_refused(version: int) -> None:
    with pytest.raises(ValueError, match="Desteklenmeyen format surumu"):
        build_file_header(start_time_utc_ns=START_NS, version=version)


# --------------------------------------------------------------------------- #
# surum 2: header CRC dogru hesaplanir
# --------------------------------------------------------------------------- #


def test_the_v2_header_carries_a_crc_over_everything_before_it() -> None:
    """ADR-011 §2.2: CRC **kendi alanı hariç**, başlığın başından hesaplanır."""
    raw = build_file_header(start_time_utc_ns=START_NS, version=2)
    stored = int.from_bytes(raw[-4:], "little")

    assert stored == header_crc32(raw[:-4])
    assert stored != 0


def test_the_v2_crc_changes_when_a_field_changes() -> None:
    first = build_file_header(start_time_utc_ns=START_NS, version=2)
    second = build_file_header(start_time_utc_ns=START_NS + 1, version=2)
    assert first[-4:] != second[-4:]


def test_a_corrupted_v2_crc_is_rejected_by_the_reader() -> None:
    """Yazıcının CRC'si gerçekten denetleniyor: tek bit bozulsa dosya reddedilir."""
    raw = bytearray(build_file_header(start_time_utc_ns=START_NS, version=2))
    raw[-1] ^= 0x01

    with pytest.raises(HeaderCrcMismatchError):
        read_validated_header(bytes(raw))


def test_the_v1_header_has_no_crc_field() -> None:
    raw = build_file_header(start_time_utc_ns=START_NS, version=1)
    assert len(raw) == EXPECTED_HEADER_SIZE_V1  # CRC alani yok


# --------------------------------------------------------------------------- #
# alan dogrulamasi
# --------------------------------------------------------------------------- #


def test_a_custom_period_is_written_and_read_back() -> None:
    """Periyot serbesttir (okuyucu nominal 125 ms'den sapmayı tanılama sayar)."""
    raw = build_file_header(start_time_utc_ns=START_NS, period_us=250_000, version=1)
    header = read_validated_header(raw)
    assert header.period_us == 250_000


@pytest.mark.parametrize("channel_count", [0, -8, 4, 16])
def test_a_channel_count_outside_the_profile_contract_is_refused(channel_count: int) -> None:
    """Profil A 8 kanalı sabitler; başka bir sayı **okunamayan** dosya üretirdi.

    Yazıcı bunu yazmak yerine baştan reddeder — bu koşuda üretim
    okuyucusunun `channel_count 4 != 8` hatası bunu ortaya çıkardı.
    """
    with pytest.raises(ValueError, match="channel_count Profil A'da"):
        build_file_header(start_time_utc_ns=START_NS, channel_count=channel_count)


def test_a_negative_start_time_is_refused() -> None:
    with pytest.raises(ValueError, match="start_time_utc_ns negatif olamaz"):
        build_file_header(start_time_utc_ns=-1)


@pytest.mark.parametrize("period_us", [0, -125_000])
def test_a_non_positive_period_is_refused(period_us: int) -> None:
    with pytest.raises(ValueError, match="period_us pozitif olmali"):
        build_file_header(start_time_utc_ns=START_NS, period_us=period_us)
