"""Şemadan çalışma zamanı yapıları — `F7-014`…`F7-018`.

Kabuller:

* `F7-014` `struct.Struct` üretimi — `calcsize` bildirilen boyuta eşit
* `F7-015` NumPy structured dtype — `itemsize` bildirilen boyuta eşit,
  alan offsetleri şemayla birebir
* `F7-016` payload kopyasız okunur
* `F7-017` parmak izi — aynı şema aynı izi, tek alan değişince farklı iz
* `F7-018` hata mesajları hangi alanı, hangi offseti ve ne yapılacağını
  söyler

Bu katmanın sessiz hatası şudur: üretilen yapı **çalışır** ama yanlış
offsetleri okur. Bayt sayısı tutar, istisna oluşmaz, değerler makul
görünür. Bu yüzden testler yalnız boyutları değil, **gerçek baytlardan
okunan değerleri** de doğrular.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest

from sonar_analyzer.io.schema.errors import SchemaMismatchError, SchemaTypeError
from sonar_analyzer.io.schema.loader import load, load_text
from sonar_analyzer.io.schema.messages import describe, describe_warnings
from sonar_analyzer.io.schema.model import Schema
from sonar_analyzer.io.schema.runtime import (
    build_dtype,
    build_reader,
    fingerprint,
    read_payload,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"


@pytest.fixture(scope="module")
def schema() -> Schema:
    return load(EXAMPLE)


def _frame_header_bytes() -> bytes:
    """Bilinen değerlerle doldurulmuş bir `FrameHeader`.

    Değerler kasten **farklı** seçildi: hepsi aynı olsaydı kaymış bir
    offset fark edilmezdi.
    """
    blob = bytearray(128)
    blob[0:4] = b"FRMC"
    struct.pack_into("<I", blob, 4, 0x11223344)  # frame_index
    struct.pack_into("<q", blob, 8, 1_700_000_000_123_456_789)  # timestamp
    struct.pack_into("<H", blob, 16, 0x00A3)  # status
    struct.pack_into("<H", blob, 18, 32)  # sensor_count
    struct.pack_into("<I", blob, 20, 820)  # sample_count
    blob[32:48] = bytes(range(16))  # cit_raw
    blob[48:72] = bytes(range(100, 124))  # tx_raw
    blob[72:120] = bytes(range(200, 248))  # platform_raw
    struct.pack_into("<I", blob, 120, 0xDEADBEEF)  # payload_crc32
    struct.pack_into("<I", blob, 124, 0xCAFEBABE)  # header_crc32
    return bytes(blob)


# --------------------------------------------------------------------------- #
# F7-014 — STRUCT URETIMI
# --------------------------------------------------------------------------- #


def test_the_reader_size_matches_the_declared_size(schema: Schema) -> None:
    """Asıl kabul: üretilen biçim bildirilen boyutu vermeli."""
    for definition in schema.structs.values():
        reader = build_reader(definition, schema.endianness)
        assert reader.size == definition.size, f"{definition.name}: boyut tutmuyor"


def test_the_reader_returns_the_right_values(schema: Schema) -> None:
    """Boyutun tutması yetmez; okunan değerler de doğru olmalı."""
    reader = build_reader(schema.struct("FrameHeader"), schema.endianness)
    values = reader.unpack(_frame_header_bytes())

    assert values["magic"] == b"FRMC"
    assert values["frame_index"] == 0x11223344
    assert values["timestamp_utc_ns"] == 1_700_000_000_123_456_789
    assert values["sensor_count"] == 32
    assert values["sample_count"] == 820
    assert values["payload_crc32"] == 0xDEADBEEF
    assert values["header_crc32"] == 0xCAFEBABE


def test_array_fields_come_back_with_every_element(schema: Schema) -> None:
    reader = build_reader(schema.struct("FrameHeader"), schema.endianness)
    values = reader.unpack(_frame_header_bytes())

    assert len(values["cit_raw"]) == 16
    assert values["cit_raw"][0] == 0
    assert values["cit_raw"][15] == 15
    assert len(values["platform_raw"]) == 48


def test_padding_fields_are_not_exposed(schema: Schema) -> None:
    """Dolgunun anlamı yoktur; kullanıcıya göstermek gürültüdür."""
    reader = build_reader(schema.struct("FrameHeader"), schema.endianness)
    assert "_pad0" not in reader.unpack(_frame_header_bytes())


def test_reading_past_the_end_is_refused(schema: Schema) -> None:
    """Kesik veriden okumak, çöp değerleri geçerli sanmak demektir."""
    reader = build_reader(schema.struct("FrameHeader"), schema.endianness)
    with pytest.raises(SchemaMismatchError, match="yeterli bayt yok"):
        reader.unpack(_frame_header_bytes()[:100])


def test_the_reader_can_start_at_an_offset(schema: Schema) -> None:
    """Frame'ler dosyada arka arkaya gelir; okuyucu kaydırılabilmeli."""
    reader = build_reader(schema.struct("FrameHeader"), schema.endianness)
    padded = b"\x00" * 7 + _frame_header_bytes()
    assert reader.unpack(padded, 7)["frame_index"] == 0x11223344


def test_bit_fields_are_decoded_from_the_status_word(schema: Schema) -> None:
    """0x00A3 = 1010 0011: tx_active, clock_locked ve gain_index=10."""
    reader = build_reader(schema.struct("FrameHeader"), schema.endianness)
    bits = reader.decode_bits("status", 0x00A3)

    assert bits["tx_active"] == 1
    assert bits["clock_locked"] == 1
    assert bits["overflow"] == 0
    assert bits["gain_index"] == 10


# --------------------------------------------------------------------------- #
# F7-015 — NUMPY DTYPE
# --------------------------------------------------------------------------- #


def test_the_dtype_itemsize_matches_the_declared_size(schema: Schema) -> None:
    """Asıl kabul: `itemsize` bildirilen boyuta eşit olmalı."""
    for definition in schema.structs.values():
        dtype = build_dtype(definition, schema.endianness)
        assert dtype.itemsize == definition.size, f"{definition.name}: itemsize tutmuyor"


def test_the_dtype_offsets_match_the_schema(schema: Schema) -> None:
    """NumPy kendi hizalamasını uygulasaydı offsetler kayardı."""
    definition = schema.struct("FrameHeader")
    dtype = build_dtype(definition, schema.endianness)
    fields = dtype.fields
    assert fields is not None
    for field in definition.fields:
        assert fields[field.name][1] == field.offset, f"{field.name}: offset kaymis"


def test_the_dtype_reads_the_same_values_as_the_struct_reader(schema: Schema) -> None:
    """İki yol aynı baytlardan aynı sonucu vermeli; vermezse biri yanlıştır."""
    definition = schema.struct("FrameHeader")
    blob = _frame_header_bytes()
    reader = build_reader(definition, schema.endianness)
    array = np.frombuffer(blob, dtype=build_dtype(definition, schema.endianness), count=1)

    values = reader.unpack(blob)
    assert int(array["frame_index"][0]) == values["frame_index"]
    assert int(array["timestamp_utc_ns"][0]) == values["timestamp_utc_ns"]
    assert bytes(array["magic"][0]) == values["magic"]


def test_an_indirect_numpy_type_is_refused() -> None:
    """`std::complex<int16_t>` NumPy'da doğrudan okunamaz; sessizce denenmemeli."""
    text = """
[schema]
id = "t"
version = 1
[structs.S]
size = 4
[[structs.S.fields]]
name = "a"
type = "std::complex<int16_t>"
offset = 0
[payload]
sensor_count = 1
frame_samples = 1
sample_type = "std::complex<float>"
"""
    schema = load_text(text)
    with pytest.raises(SchemaTypeError, match="elle birlestirilmeli"):
        build_dtype(schema.struct("S"), schema.endianness)


# --------------------------------------------------------------------------- #
# F7-016 — PAYLOAD OKUMA
# --------------------------------------------------------------------------- #


def _payload_bytes(sensors: int, samples: int) -> bytes:
    values = np.arange(sensors * samples, dtype=np.float32)
    buffer = np.empty(sensors * samples, dtype=np.complex64)
    buffer.real = values
    buffer.imag = -values
    return buffer.tobytes()


def test_the_payload_comes_back_as_sensor_by_sample(schema: Schema) -> None:
    """Asıl kabul: (32, 820) complex64."""
    payload = schema.payload
    array = read_payload(schema, _payload_bytes(payload.sensor_count, payload.frame_samples))

    assert array.shape == (payload.sensor_count, payload.frame_samples)
    assert array.dtype == np.complex64


def test_the_payload_is_read_without_a_copy(schema: Schema) -> None:
    """1,17 GiB'lik bir kayıtta kopya almak belleği ikiye katlardı."""
    payload = schema.payload
    blob = _payload_bytes(payload.sensor_count, payload.frame_samples)
    array = read_payload(schema, blob)

    assert array.base is not None, "kopya alinmis"


def test_sensor_major_and_sample_major_differ(schema: Schema) -> None:
    """Asıl risk: yanlış yerleşim hiçbir boyut denetimini düşürmez.

    İkisi de (32, 820) döner ve aynı bayt sayısını okur. Yalnız değerler
    yer değiştirir — yani sensörler birbirine karışır.
    """
    payload = schema.payload
    blob = _payload_bytes(payload.sensor_count, payload.frame_samples)
    major = read_payload(schema, blob)

    other = load_text(
        EXAMPLE.read_text(encoding="utf-8").replace(
            'layout = "sensor_major"', 'layout = "sample_major"'
        )
    )
    minor = read_payload(other, blob)

    assert major.shape == minor.shape
    assert not np.array_equal(major, minor), "iki yerlesim ayni sonucu veriyor"


def test_sample_major_is_the_transpose(schema: Schema) -> None:
    payload = schema.payload
    blob = _payload_bytes(payload.sensor_count, payload.frame_samples)
    other = load_text(
        EXAMPLE.read_text(encoding="utf-8").replace(
            'layout = "sensor_major"', 'layout = "sample_major"'
        )
    )
    expected = (
        np.frombuffer(blob, dtype="<c8").reshape(payload.frame_samples, payload.sensor_count).T
    )
    assert np.array_equal(read_payload(other, blob), expected)


def test_a_short_payload_is_refused(schema: Schema) -> None:
    payload = schema.payload
    blob = _payload_bytes(payload.sensor_count, payload.frame_samples)[:-8]
    with pytest.raises(SchemaMismatchError, match="yeterli bayt yok"):
        read_payload(schema, blob)


def test_the_payload_can_start_at_an_offset(schema: Schema) -> None:
    """Yük, frame başlığından hemen sonra gelir."""
    payload = schema.payload
    blob = b"\x00" * 128 + _payload_bytes(payload.sensor_count, payload.frame_samples)
    array = read_payload(schema, blob, 128)
    assert array[0, 0] == 0
    assert array.shape == (payload.sensor_count, payload.frame_samples)


def test_the_frame_byte_count_matches_the_budget(schema: Schema) -> None:
    assert schema.payload.frame_bytes == 209_920


# --------------------------------------------------------------------------- #
# F7-017 — PARMAK IZI
# --------------------------------------------------------------------------- #


def test_the_same_schema_gives_the_same_fingerprint(schema: Schema) -> None:
    assert fingerprint(schema) == fingerprint(load(EXAMPLE))


def test_a_changed_offset_changes_the_fingerprint() -> None:
    """Asıl kabul: tek alan değişince parmak izi değişmeli."""
    text = EXAMPLE.read_text(encoding="utf-8")
    original = fingerprint(load_text(text))
    moved = text.replace(
        'name = "cit_raw"\ntype = "uint8_t"\noffset = 32\ncount = 16',
        'name = "cit_raw"\ntype = "uint8_t"\noffset = 32\ncount = 15',
    )
    assert moved != text, "degistirilecek alan bulunamadi"
    # 15 bayt yapinca bosluk olusur; boyut yine 128 kalir ama iz degismeli.
    assert fingerprint(load_text(moved)) != original


def test_a_changed_type_changes_the_fingerprint() -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    original = fingerprint(load_text(text))
    swapped = text.replace(
        'name = "sensor_count"\ntype = "uint16_t"\noffset = 18',
        'name = "sensor_count"\ntype = "int16_t"\noffset = 18',
    )
    assert fingerprint(load_text(swapped)) != original


def test_a_changed_enum_value_changes_the_fingerprint() -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    original = fingerprint(load_text(text))
    swapped = text.replace("TX = 1\nRX = 2", "TX = 2\nRX = 1")
    assert fingerprint(load_text(swapped)) != original


def test_a_comment_change_does_not_change_the_fingerprint() -> None:
    """Bir yazım düzeltmesi bütün önbellekleri geçersiz kılmamalı."""
    text = EXAMPLE.read_text(encoding="utf-8")
    original = fingerprint(load_text(text))
    edited = text.replace(
        'description = "Klasor tabanli Tx/Rx kayit — bicim ornegi"',
        'description = "Klasor tabanli Tx/Rx kayit — BICIM ORNEGI (yazim duzeltildi)"',
    )
    assert edited != text, "degistirilecek aciklama bulunamadi"
    assert fingerprint(load_text(edited)) == original


def test_the_fingerprint_is_short_and_hex(schema: Schema) -> None:
    value = fingerprint(schema)
    assert len(value) == 16
    assert all(character in "0123456789abcdef" for character in value)


# --------------------------------------------------------------------------- #
# F7-018 — KULLANICIYA TASINAN MESAJLAR
# --------------------------------------------------------------------------- #


def test_an_unknown_type_message_says_what_to_do() -> None:
    report = describe(SchemaTypeError("widget_t", field="frame_index"))
    assert "frame_index" in report.detail
    assert "widget_t" in report.detail
    assert "toml-schema.md" in report.action
    assert report.recoverable is False


def test_a_forbidden_type_message_carries_the_hint() -> None:
    """Yasak bir tipin gerekçesi mesajda görünmeli."""
    report = describe(SchemaTypeError("long", hint="platforma bagli; int64_t yazin"))
    assert "int64_t" in report.detail
    assert "bilinçli olarak desteklenmiyor" in report.detail


def test_a_layout_error_message_names_the_struct() -> None:
    with pytest.raises(Exception):  # noqa: B017 - asagida yakalanip inceleniyor
        load_text("[schema]\nid='t'\nversion=1\n[structs.S]\nsize=4\n")
    try:
        load_text(
            "[schema]\nid='t'\nversion=1\n"
            "[structs.S]\nsize=8\n"
            '[[structs.S.fields]]\nname="a"\ntype="uint32_t"\noffset=0\n'
            '[[structs.S.fields]]\nname="b"\ntype="uint32_t"\noffset=2\n'
            "[payload]\nsensor_count=1\nframe_samples=1\n"
            'sample_type="std::complex<float>"\n'
        )
    except Exception as error:
        report = describe(error)  # type: ignore[arg-type]
        assert "S" in report.title
        assert "sessizce yanlış" in report.detail
        assert "§4" in report.action
    else:  # pragma: no cover
        pytest.fail("ortusme hatasi beklenirdi")


def test_a_mismatch_message_explains_the_silent_risk() -> None:
    """Bu hata engellenmese veri hatasız ama yanlış okunurdu."""
    report = describe(SchemaMismatchError("boyut tutmuyor", expected=128, found=120))
    assert "kaymış hâlde" in report.detail
    assert "hatasız görünürdü" in report.detail
    assert "profile-c.md" in report.action


def test_every_report_answers_all_three_questions() -> None:
    """Ne oldu, neden önemli, ne yapmalı — üçü birden."""
    for error in (
        SchemaTypeError("widget_t"),
        SchemaMismatchError("x", expected=1, found=2),
    ):
        report = describe(error)
        assert report.title
        assert len(report.detail) > 40
        assert len(report.action) > 20
        assert "Ne yapmalı:" in report.as_text()


def test_no_warnings_produces_no_report() -> None:
    """Boş bir diyalog göstermek gürültüdür."""
    assert describe_warnings(()) is None


def test_warnings_are_collected_into_one_recoverable_report() -> None:
    report = describe_warnings(("S: 4..8 arasinda bildirilmemis 4 bayt bosluk",))
    assert report is not None
    assert report.recoverable is True
    assert "1 uyarı" in report.title
    assert "4 bayt bosluk" in report.detail
    assert "§4.1" in report.action
