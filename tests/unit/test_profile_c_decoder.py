"""Profil C çözücüsü — `F7-019`…`F7-028`.

Kabuller: dosya başlığı ve frame başlığı şemadan çözülür, `complex64`
yük kopyasız okunur, frame CRC'si doğrulanır, kesik dosya raporlanır,
indeks uyuşmazlığı bildirilir ve şema ile kayıt ayrışırsa okuma durur.

Bu çözücünün sessiz hatası şudur: **yanlış bir şemayla dosya hatasız
okunur.** Bayt sayısı tutar, CRC tutar, hiçbir istisna oluşmaz ve her
alan kaymış hâlde çıkar. Bu yüzden testlerin çoğunluğu üç kapının
gerçekten durdurduğunu gösterir.

Karşı yön de tutulur: bozuk bir frame kaydın tamamını düşürmemeli.
Tek bir CRC hatası yüzünden 10 dakikalık bir kaydı okunamaz saymak,
veriyi korumak değil yok etmektir.
"""

from __future__ import annotations

import struct
from pathlib import Path
from zlib import crc32

import numpy as np
import pytest

from sonar_analyzer.io.decoders.profile_c import (
    check_frame_sequence,
    decode_file,
    measure_drift,
)
from sonar_analyzer.io.schema.errors import SchemaMismatchError
from sonar_analyzer.io.schema.loader import load_text
from sonar_analyzer.io.schema.model import Schema

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"

#: Test dosyalari kucuk tutulur: gercek 32x820 yerine 4x8.
#: Gercek boyut her testte 205 KiB uretir ve hicbir sey kanitlamaz.
SMALL = (
    EXAMPLE.read_text(encoding="utf-8")
    .replace("sensor_count = 32", "sensor_count = 4")
    .replace("frame_samples = 820", "frame_samples = 8")
)


@pytest.fixture(scope="module")
def schema() -> Schema:
    return load_text(SMALL)


def _payload(schema: Schema, seed: int) -> bytes:
    """Frame yükü; her frame farklı olsun diye `seed` ile kaydırılır."""
    payload = schema.payload
    count = payload.sensor_count * payload.frame_samples
    values = np.arange(seed, seed + count, dtype=np.float32)
    buffer = np.empty(count, dtype=np.complex64)
    buffer.real = values
    buffer.imag = -values
    return buffer.tobytes()


def _frame(schema: Schema, index: int, *, crc: int | None = None, status: int = 0x0003) -> bytes:
    """Bir frame: başlık + yük."""
    body = _payload(schema, index * 100)
    blob = bytearray(schema.struct("FrameHeader").size)
    blob[0:4] = b"FRMC"
    struct.pack_into("<I", blob, 4, index)
    struct.pack_into("<q", blob, 8, 1_700_000_000_000_000_000 + index * 100_097_656)
    struct.pack_into("<H", blob, 16, status)
    struct.pack_into("<H", blob, 18, schema.payload.sensor_count)
    struct.pack_into("<I", blob, 20, schema.payload.frame_samples)
    struct.pack_into("<I", blob, 120, crc32(body) & 0xFFFFFFFF if crc is None else crc)
    return bytes(blob) + body


def _file(schema: Schema, frames: int, *, first: int = 0, **frame_kwargs: int) -> bytes:
    """Bir saniyelik dosya: dosya başlığı + frame'ler."""
    blob = bytearray(schema.struct("FileHeader").size)
    blob[0:8] = b"SNRPROFC"
    struct.pack_into("<H", blob, 8, schema.version)
    struct.pack_into("<H", blob, 10, schema.struct("FileHeader").size)
    struct.pack_into("<B", blob, 12, 2)  # stream_kind = RX
    struct.pack_into("<H", blob, 16, schema.payload.sensor_count)
    struct.pack_into("<H", blob, 18, schema.payload.frame_samples)
    struct.pack_into("<I", blob, 20, frames)
    struct.pack_into("<I", blob, 24, 8192)
    struct.pack_into("<q", blob, 32, 1_700_000_000_000_000_000)
    body = b"".join(_frame(schema, first + i, **frame_kwargs) for i in range(frames))
    return bytes(blob) + body


# --------------------------------------------------------------------------- #
# F7-019 / F7-020 — BASLIKLAR
# --------------------------------------------------------------------------- #


def test_a_well_formed_file_decodes(schema: Schema) -> None:
    """Karşı yön: doğru dosya sorunsuz çözülmeli."""
    decoded = decode_file(schema, _file(schema, 10))

    assert decoded.frame_count == 10
    assert decoded.issues == ()
    assert decoded.dropped_bytes == 0


def test_the_file_header_fields_are_decoded(schema: Schema) -> None:
    decoded = decode_file(schema, _file(schema, 3))

    assert decoded.header["magic"] == b"SNRPROFC"
    assert decoded.header["frame_count"] == 3
    assert decoded.header["sample_rate_hz"] == 8192
    assert decoded.header["sensor_count"] == schema.payload.sensor_count


def test_the_frame_header_fields_are_decoded(schema: Schema) -> None:
    frames = decode_file(schema, _file(schema, 3)).frames

    assert [f.index for f in frames] == [0, 1, 2]
    assert frames[0].header["magic"] == b"FRMC"
    assert frames[1].header["sample_count"] == schema.payload.frame_samples


def test_the_canonical_time_comes_from_the_timestamp(schema: Schema) -> None:
    """`D-33`: zaman frame sayacından değil başlıktan türer."""
    frames = decode_file(schema, _file(schema, 3)).frames

    assert frames[0].timestamp_ns == 1_700_000_000_000_000_000
    assert frames[1].timestamp_ns - frames[0].timestamp_ns == 100_097_656


def test_the_status_bits_are_decoded(schema: Schema) -> None:
    frame = decode_file(schema, _file(schema, 1, status=0x00A3)).frames[0]

    assert frame.flags["tx_active"] == 1
    assert frame.flags["clock_locked"] == 1
    assert frame.flags["overflow"] == 0
    assert frame.flags["gain_index"] == 10


def test_a_file_shorter_than_its_header_is_refused(schema: Schema) -> None:
    with pytest.raises(SchemaMismatchError, match="dosya basligi"):
        decode_file(schema, b"\x00" * 10)


# --------------------------------------------------------------------------- #
# F7-021 / F7-022 — YUK
# --------------------------------------------------------------------------- #


def test_the_payload_shape_follows_the_schema(schema: Schema) -> None:
    frame = decode_file(schema, _file(schema, 1)).frames[0]

    assert frame.samples.shape == (schema.payload.sensor_count, schema.payload.frame_samples)
    assert frame.samples.dtype == np.complex64


def test_the_payload_is_not_copied(schema: Schema) -> None:
    """1,17 GiB'lik bir kayıtta kopya almak belleği ikiye katlardı."""
    frame = decode_file(schema, _file(schema, 1)).frames[0]

    assert frame.samples.base is not None


def test_each_frame_gets_its_own_payload(schema: Schema) -> None:
    """Bütün frame'ler aynı veriyi gösterseydi bir offset hatası gizlenirdi."""
    frames = decode_file(schema, _file(schema, 3)).frames

    assert not np.array_equal(frames[0].samples, frames[1].samples)
    # Deger complex: 100-100j. Gercek kismi karsilastirmak, sanal kismin
    # sessizce atlanmasini onler.
    assert frames[0].samples[0, 0] == 0 + 0j
    assert frames[1].samples[0, 0] == 100 - 100j
    assert frames[2].samples[0, 0] == 200 - 200j


# --------------------------------------------------------------------------- #
# F7-023 — CRC
# --------------------------------------------------------------------------- #


def test_a_matching_crc_passes(schema: Schema) -> None:
    decoded = decode_file(schema, _file(schema, 4))

    assert decoded.crc_checked is True
    assert all(frame.crc_ok for frame in decoded.frames)


def test_a_bad_crc_is_flagged_but_the_frame_is_kept(schema: Schema) -> None:
    """Asıl kabul: bozuk frame işaretlenir, atılmaz."""
    blob = bytearray(_file(schema, 3))
    frame_size = schema.struct("FrameHeader").size + schema.payload.frame_bytes
    bad_at = schema.struct("FileHeader").size + frame_size  # 1. frame
    struct.pack_into("<I", blob, bad_at + 120, 0xDEADBEEF)

    decoded = decode_file(schema, bytes(blob))

    assert decoded.frame_count == 3, "bozuk frame atilmis"
    assert decoded.frames[1].crc_ok is False
    assert decoded.frames[0].crc_ok is True
    assert decoded.frames[2].crc_ok is True


def test_a_bad_crc_reports_both_values(schema: Schema) -> None:
    """Hangi değerin beklendiği yazılmazsa sorun teşhis edilemez."""
    blob = bytearray(_file(schema, 1))
    struct.pack_into("<I", blob, schema.struct("FileHeader").size + 120, 0xDEADBEEF)

    issues = decode_file(schema, bytes(blob)).issues

    assert len(issues) == 1
    assert issues[0].code == "CRC_ERROR"
    assert "0xdeadbeef" in issues[0].detail
    assert "beklenen" in issues[0].detail


def test_crc_verification_can_be_switched_off(schema: Schema) -> None:
    """Büyük bir kaydı hızlı taramak için; ama atlandığı raporlanır."""
    blob = bytearray(_file(schema, 1))
    struct.pack_into("<I", blob, schema.struct("FileHeader").size + 120, 0xDEADBEEF)

    decoded = decode_file(schema, bytes(blob), verify_crc=False)

    assert decoded.issues == ()
    assert decoded.crc_checked is False, "atlanan dogrulama gecmis sayilmamali"


# --------------------------------------------------------------------------- #
# F7-024 — KESIK DOSYA
# --------------------------------------------------------------------------- #


def test_a_truncated_last_frame_is_dropped_and_reported(schema: Schema) -> None:
    """Asıl kabul: tam frame'ler kullanılır, kaç bayt atıldığı söylenir."""
    blob = _file(schema, 3)[:-20]

    decoded = decode_file(schema, blob)

    assert decoded.frame_count == 2
    assert decoded.dropped_bytes > 0
    assert any(issue.code == "TRUNCATED" for issue in decoded.issues)


def test_the_truncation_message_names_the_byte_count(schema: Schema) -> None:
    decoded = decode_file(schema, _file(schema, 2)[:-20])
    issue = next(i for i in decoded.issues if i.code == "TRUNCATED")

    assert str(decoded.dropped_bytes) in issue.detail
    assert "atildi" in issue.detail


def test_a_file_cut_inside_its_first_frame_still_returns_its_header(schema: Schema) -> None:
    """Başlık okunabiliyorsa kayıt hakkında bir şey söylenebilir.

    Dosya bir frame bildiriyor ama ilk frame'in ortasında kesilmiş.
    Tam frame yok; yine de başlık ve kesinti raporu elde edilir.
    """
    header_size = schema.struct("FileHeader").size
    blob = _file(schema, 1)[: header_size + 30]

    decoded = decode_file(schema, blob)

    assert decoded.frame_count == 0
    assert decoded.header["magic"] == b"SNRPROFC"
    assert decoded.dropped_bytes == 30
    assert any(issue.code == "TRUNCATED" for issue in decoded.issues)


# --------------------------------------------------------------------------- #
# F7-025 — INDEKS UYUSMAZLIGI
# --------------------------------------------------------------------------- #


def test_a_consistent_sequence_reports_nothing(schema: Schema) -> None:
    decoded = decode_file(schema, _file(schema, 5))

    assert check_frame_sequence(decoded) == []


def test_a_gap_in_the_frame_index_is_reported(schema: Schema) -> None:
    blob = bytearray(_file(schema, 3))
    frame_size = schema.struct("FrameHeader").size + schema.payload.frame_bytes
    second = schema.struct("FileHeader").size + frame_size
    struct.pack_into("<I", blob, second + 4, 7)  # 1 yerine 7

    issues = check_frame_sequence(decode_file(schema, bytes(blob)))

    assert any(issue.code == "GAP_BEFORE" for issue in issues)


def test_a_backward_index_is_reported_separately(schema: Schema) -> None:
    """Geriye giden indeks, boşluktan farklı bir sorundur."""
    blob = bytearray(_file(schema, 3))
    frame_size = schema.struct("FrameHeader").size + schema.payload.frame_bytes
    second = schema.struct("FileHeader").size + frame_size
    struct.pack_into("<I", blob, second + 4, 0)

    issues = check_frame_sequence(decode_file(schema, bytes(blob)))

    assert any(issue.code == "INDEX_BACKWARD" for issue in issues)


def test_a_file_counter_mismatch_is_reported(schema: Schema) -> None:
    """`RxData00007.bin` içinde 70'ten başlamayan indeks, karışmış dosya demektir."""
    decoded = decode_file(schema, _file(schema, 10, first=0))

    issues = check_frame_sequence(decoded, file_index=7)

    assert any(issue.code == "INDEX_MISMATCH" for issue in issues)
    assert "70" in issues[0].detail


def test_a_matching_file_counter_reports_nothing(schema: Schema) -> None:
    decoded = decode_file(schema, _file(schema, 10, first=70))

    assert check_frame_sequence(decoded, file_index=7) == []


# --------------------------------------------------------------------------- #
# UC KAPI — SEMA ILE KAYIT AYRISMASI
# --------------------------------------------------------------------------- #


def test_a_different_schema_version_stops_the_read(schema: Schema) -> None:
    """İkinci kapı: sürüm tutmuyorsa okuma başlamaz."""
    blob = bytearray(_file(schema, 2))
    struct.pack_into("<H", blob, 8, 99)

    with pytest.raises(SchemaMismatchError, match="sema surumuyle"):
        decode_file(schema, bytes(blob))


def test_a_wrong_sensor_count_stops_the_read(schema: Schema) -> None:
    """Üçüncü kapı: dosya başlığı şemayla çelişiyorsa durur."""
    blob = bytearray(_file(schema, 2))
    struct.pack_into("<H", blob, 16, 99)

    with pytest.raises(SchemaMismatchError, match="sensor_count"):
        decode_file(schema, bytes(blob))


def test_a_changed_frame_header_is_caught_by_the_magic_gate(schema: Schema) -> None:
    """Asıl kabul: şema kimliği doğru olsa bile okuma durmalı.

    C++ tarafı frame başlığına bir alan eklemiş ama sürümü artırmamışsa
    ikinci kapı geçer. Boyut denklemi de geçebilir: eksik bayt bir
    frame'den azsa kesik dosyadan ayırt edilemez.

    Duran şey frame sihirli sayısıdır. Frame boyutu bir bayt bile
    kaysa, ikinci frame'in sihirli sayısı beklenen offsette bulunmaz.
    Bu, kesik dosya ile yanlış şemayı ayıran işarettir.
    """
    bigger = load_text(
        SMALL.replace("[structs.FrameHeader]\nsize = 128", "[structs.FrameHeader]\nsize = 132")
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

    with pytest.raises(SchemaMismatchError, match="sihirli sayisi"):
        decode_file(bigger, _file(schema, 4))


def test_the_declared_frame_count_must_match_the_file_size(schema: Schema) -> None:
    blob = bytearray(_file(schema, 3))
    struct.pack_into("<I", blob, 20, 5)

    with pytest.raises(SchemaMismatchError, match="boyut denklemi"):
        decode_file(schema, bytes(blob))


def test_a_file_without_a_version_field_is_not_blocked() -> None:
    """Kimlik alanı yoksa ikinci kapı atlanır; üçüncü kapı yine çalışır.

    Her şemanın sürüm alanı taşıması zorunlu değildir. Zorunlu kılmak,
    sürüm alanı olmayan bir C++ struct'ını okunamaz kılardı.
    """
    text = """
[schema]
id = "t"
version = 3
endianness = "little"
packing = "packed"

[structs.FileHeader]
size = 8
[[structs.FileHeader.fields]]
name = "magic"
type = "char[N]"
count = 8
offset = 0

[structs.FrameHeader]
size = 8
[[structs.FrameHeader.fields]]
name = "frame_index"
type = "uint32_t"
offset = 0
[[structs.FrameHeader.fields]]
name = "_pad"
type = "uint32_t"
offset = 4

[payload]
sensor_count = 2
frame_samples = 2
sample_type = "std::complex<float>"
layout = "sensor_major"
"""
    plain = load_text(text)
    frame = struct.pack("<II", 0, 0) + b"\x00" * plain.payload.frame_bytes
    decoded = decode_file(plain, b"MAGIC123" + frame)

    assert decoded.frame_count == 1
    assert decoded.crc_checked is False, "CRC alani yokken dogrulama gecmis sayilmamali"


# --------------------------------------------------------------------------- #
# BASLIK CRC'SI OLUMCULDUR — ADR-011
# --------------------------------------------------------------------------- #


def _with_header_crc(schema: Schema, blob: bytes) -> bytes:
    """Dosya başlığının CRC alanını doğru değerle doldurur."""
    size = schema.struct("FileHeader").size
    body = bytearray(blob)
    block = bytearray(body[:size])
    block[60:64] = b"\x00\x00\x00\x00"
    struct.pack_into("<I", body, 60, crc32(bytes(block)) & 0xFFFFFFFF)
    return bytes(body)


def test_a_correct_header_crc_passes(schema: Schema) -> None:
    """Karşı yön: doğru CRC okumayı engellememeli."""
    decoded = decode_file(schema, _with_header_crc(schema, _file(schema, 2)))

    assert decoded.frame_count == 2


def test_a_bad_header_crc_stops_the_read(schema: Schema) -> None:
    """Asıl kabul: başlık CRC'si ölümcüldür (`ADR-011`).

    Kayıt CRC'si bir frame'i işaretler ve okumaya devam edilir. Başlık
    bozuksa sensör sayısı, frame sayısı ve örnekleme hızı güvenilmezdir.
    """
    blob = bytearray(_with_header_crc(schema, _file(schema, 2)))
    struct.pack_into("<I", blob, 60, 0x12345678)

    with pytest.raises(SchemaMismatchError, match="CRC'si tutmuyor"):
        decode_file(schema, bytes(blob))


def test_a_zero_header_crc_is_treated_as_not_computed(schema: Schema) -> None:
    """Sıfırı doğru CRC sayıp reddetmek, CRC yazmayan üreticiyi dışlardı."""
    decoded = decode_file(schema, _file(schema, 2))  # CRC alani sifir

    assert decoded.frame_count == 2


def test_the_header_crc_excludes_its_own_field(schema: Schema) -> None:
    """Kendi alanını kapsasaydı doğru CRC'yi hesaplamak imkânsız olurdu."""
    blob = _with_header_crc(schema, _file(schema, 1))
    size = schema.struct("FileHeader").size
    naive = crc32(blob[:size]) & 0xFFFFFFFF
    stored = struct.unpack_from("<I", blob, 60)[0]

    assert stored != naive, "CRC kendi alanini da kapsiyor"


# --------------------------------------------------------------------------- #
# F7-026 — TIMESTAMP ILE SAYAC ARASINDAKI KAYMA
# --------------------------------------------------------------------------- #


def test_the_nominal_period_comes_from_the_schema(schema: Schema) -> None:
    """820/8192 = 100,0977 ms; 100 ms değil."""
    decoded = decode_file(schema, _file(schema, 5))
    drift = measure_drift(decoded, 8192.0, 820)

    assert abs(drift.nominal_period_ns - 100_097_656.25) < 1.0


def test_a_timestamp_on_the_nominal_grid_reports_no_drift(schema: Schema) -> None:
    """Karşı yön: tam nominal adımda sapma sıfır olmalı."""
    decoded = decode_file(schema, _file(schema, 5))
    drift = measure_drift(decoded, 8192.0, 820)

    assert drift.measurable is True
    assert abs(drift.ppm) < 1.0, f"beklenmeyen sapma: {drift.ppm}"


def test_a_hundred_millisecond_grid_reports_minus_975_ppm(schema: Schema) -> None:
    """Asıl kabul: cihaz 100 ms ızgarasına yazıyorsa −975,6 ppm çıkar."""
    blob = bytearray(_file(schema, 5))
    frame_size = schema.struct("FrameHeader").size + schema.payload.frame_bytes
    base = schema.struct("FileHeader").size
    for index in range(5):
        struct.pack_into(
            "<q",
            blob,
            base + index * frame_size + 8,
            1_700_000_000_000_000_000 + index * 100_000_000,
        )

    drift = measure_drift(decode_file(schema, bytes(blob)), 8192.0, 820)

    assert abs(drift.ppm + 975.6) < 0.5, f"gercek {drift.ppm}"


def test_the_sign_says_which_side_is_fast(schema: Schema) -> None:
    """İşaret silinirse hangi tarafın hızlı olduğu kaybolur."""
    blob = bytearray(_file(schema, 3))
    frame_size = schema.struct("FrameHeader").size + schema.payload.frame_bytes
    base = schema.struct("FileHeader").size
    for index in range(3):
        struct.pack_into(
            "<q",
            blob,
            base + index * frame_size + 8,
            1_700_000_000_000_000_000 + index * 110_000_000,
        )

    drift = measure_drift(decode_file(schema, bytes(blob)), 8192.0, 820)

    assert drift.ppm > 0, "timestamp nominalden yavas ise sapma pozitif olmali"


def test_a_single_frame_cannot_be_measured(schema: Schema) -> None:
    """Sıfır döndürüp "sapma yok" demek, ölçülmemişi ölçülmüş göstermek olurdu."""
    drift = measure_drift(decode_file(schema, _file(schema, 1)), 8192.0, 820)

    assert drift.measurable is False
    assert np.isnan(drift.ppm)


def test_the_accumulated_drift_matches_the_documented_figure(schema: Schema) -> None:
    """10 dakikada 0,586 s — belgedeki sayı buradan türemeli."""
    blob = bytearray(_file(schema, 5))
    frame_size = schema.struct("FrameHeader").size + schema.payload.frame_bytes
    base = schema.struct("FileHeader").size
    for index in range(5):
        struct.pack_into(
            "<q",
            blob,
            base + index * frame_size + 8,
            1_700_000_000_000_000_000 + index * 100_000_000,
        )

    drift = measure_drift(decode_file(schema, bytes(blob)), 8192.0, 820)
    accumulated_s = abs(drift.accumulated_ns(600.0)) / 1e9

    assert abs(accumulated_s - 0.586) < 0.002, f"gercek {accumulated_s:.4f} s"
