"""TOML şema yükleyicisi ve doğrulamaları — `F7-008`…`F7-013`.

Kabuller:

* `F7-008` şema yükleyici ve sürüm alanı — kimliksiz şema reddedilir
* `F7-009` enum çözümleyici — yinelenen değer açık hata verir
* `F7-010` struct alan çözümleyici — eksik alan reddedilir
* `F7-011` offset çakışması ve boşluk denetimi
* `F7-012` bildirilen boyut ile hesaplanan boyut uyuşmazlığı
* `F7-013` hizalama ihlali denetimi

Bir doğrulayıcının en tehlikeli hâli her şeyi geçirmesidir. Bu yüzden
testlerin çoğu **bozuk bir şema kurup reddedildiğini** doğrular; geçerli
şemanın geçtiğini gösteren testler azınlıktadır ve karşı yönü tutar.

Her hata mesajı ayrıca sınanır: mesaj hangi struct'ı, hangi alanı ve
hangi offseti söylemiyorsa, yüz alanlı bir dosyada işe yaramaz.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from sonar_analyzer.io.schema.errors import (
    SchemaLayoutError,
    SchemaTypeError,
    SchemaValueError,
)
from sonar_analyzer.io.schema.loader import load, load_text

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "schemas" / "profile-c.example.toml"

MINIMAL = """
[schema]
id = "test"
version = 1
endianness = "little"
packing = "packed"

[structs.Head]
size = 8
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 4

[payload]
sensor_count = 32
frame_samples = 820
sample_type = "std::complex<float>"
layout = "sensor_major"
"""


def _variant(*, schema: str = "", struct_body: str = "", payload: str = "") -> str:
    """`MINIMAL` şemasının bir bölümünü değiştirir."""
    text = MINIMAL
    if schema:
        text = text.replace('[schema]\nid = "test"\nversion = 1', schema)
    if struct_body:
        start = text.index("[structs.Head]")
        end = text.index("[payload]")
        text = text[:start] + struct_body + "\n" + text[end:]
    if payload:
        text = text[: text.index("[payload]")] + payload
    return text


# --------------------------------------------------------------------------- #
# F7-008 — YUKLEYICI VE SURUM ALANI
# --------------------------------------------------------------------------- #


def test_the_example_schema_loads() -> None:
    """Karşı yön: geçerli bir şema geçmeli."""
    schema = load(EXAMPLE)
    assert schema.id == "sonar-profile-c"
    assert schema.version == 1
    assert schema.packed is True


def test_the_example_schema_has_no_layout_warnings() -> None:
    """Örnek şema kendi kurallarını çiğnememeli."""
    assert load(EXAMPLE).warnings == ()


def test_the_loaded_struct_format_matches_the_declared_size() -> None:
    """Asıl kabul: üretilen `struct` biçimi bildirilen boyutu vermeli."""
    schema = load(EXAMPLE)
    for definition in schema.structs.values():
        fmt = definition.struct_format(schema.endianness)
        assert struct.calcsize(fmt) == definition.size, f"{definition.name} boyutu tutmuyor"


def test_a_schema_without_an_id_is_rejected() -> None:
    """Kimliksiz şema, hangi kayda ait olduğu bilinmeyen şemadır."""
    with pytest.raises(SchemaValueError, match="id"):
        load_text(_variant(schema="[schema]\nversion = 1"))


def test_a_schema_without_a_version_is_rejected() -> None:
    with pytest.raises(SchemaValueError, match="version"):
        load_text(_variant(schema='[schema]\nid = "test"'))


def test_a_non_integer_version_is_rejected() -> None:
    """`version = "1"` sessizce kabul edilirse karşılaştırma hep düşer."""
    with pytest.raises(SchemaValueError, match="tamsayi"):
        load_text(_variant(schema='[schema]\nid = "test"\nversion = "1"'))


def test_a_boolean_is_not_accepted_as_an_integer() -> None:
    """Python'da `True == 1`; `isinstance(True, int)` da doğrudur."""
    with pytest.raises(SchemaValueError, match="tamsayi"):
        load_text(_variant(schema='[schema]\nid = "test"\nversion = true'))


@pytest.mark.parametrize("value", ["middle", "LITTLE", ""])
def test_an_unknown_endianness_is_rejected(value: str) -> None:
    with pytest.raises(SchemaValueError, match="endianness"):
        load_text(MINIMAL.replace('endianness = "little"', f'endianness = "{value}"'))


@pytest.mark.parametrize("value", ["tight", "aligned"])
def test_an_unknown_packing_is_rejected(value: str) -> None:
    with pytest.raises(SchemaValueError, match="packing"):
        load_text(MINIMAL.replace('packing = "packed"', f'packing = "{value}"'))


def test_a_big_endian_schema_produces_a_big_endian_format() -> None:
    schema = load_text(MINIMAL.replace('endianness = "little"', 'endianness = "big"'))
    assert schema.struct("Head").struct_format(schema.endianness).startswith(">")


def test_a_schema_without_structs_is_rejected() -> None:
    text = MINIMAL[: MINIMAL.index("[structs.Head]")] + MINIMAL[MINIMAL.index("[payload]") :]
    with pytest.raises(SchemaValueError, match="structs"):
        load_text(text)


def test_a_schema_without_a_payload_is_rejected() -> None:
    with pytest.raises(SchemaValueError, match="payload"):
        load_text(MINIMAL[: MINIMAL.index("[payload]")])


# --------------------------------------------------------------------------- #
# F7-009 — ENUM COZUMLEYICI
# --------------------------------------------------------------------------- #


def test_enums_are_resolved_with_their_underlying_type() -> None:
    schema = load(EXAMPLE)
    assert schema.enums["StreamKind"].underlying.cpp == "uint8_t"
    assert schema.enums["StreamKind"].values["TX"] == 1


def test_an_enum_maps_values_back_to_names() -> None:
    schema = load(EXAMPLE)
    assert schema.enums["StreamKind"].name_of(2) == "RX"


def test_an_unknown_enum_value_is_not_silently_renamed() -> None:
    """Bilinmeyeni `UNKNOWN`'a çevirmek, bozuk kaydı geçerliden ayırt edilemez kılardı."""
    schema = load(EXAMPLE)
    label = schema.enums["StreamKind"].name_of(99)
    assert "bilinmeyen" in label
    assert "99" in label


def test_a_duplicate_enum_value_is_rejected() -> None:
    """Asıl kabul: yinelenen değer, geri eşlemeyi belirsiz kılar."""
    text = (
        MINIMAL
        + """
[enums.Bad]
underlying = "uint8_t"
[enums.Bad.values]
A = 1
B = 1
"""
    )
    with pytest.raises(SchemaValueError, match="ayni degeri"):
        load_text(text)


def test_an_enum_value_outside_its_underlying_range_is_rejected() -> None:
    text = (
        MINIMAL
        + """
[enums.Bad]
underlying = "uint8_t"
[enums.Bad.values]
TOO_BIG = 256
"""
    )
    with pytest.raises(SchemaValueError, match="sigmiyor"):
        load_text(text)


def test_an_enum_with_an_unknown_underlying_type_is_rejected() -> None:
    text = (
        MINIMAL
        + """
[enums.Bad]
underlying = "long"
[enums.Bad.values]
A = 1
"""
    )
    with pytest.raises(SchemaTypeError, match="long"):
        load_text(text)


def test_an_empty_enum_is_rejected() -> None:
    text = (
        MINIMAL
        + """
[enums.Bad]
underlying = "uint8_t"
[enums.Bad.values]
"""
    )
    with pytest.raises(SchemaValueError, match="bos olmayan"):
        load_text(text)


def test_a_field_referring_to_an_undefined_enum_is_rejected() -> None:
    """Tanımsız bir enum adı, okuma anında sessizce ham sayı gösterirdi."""
    body = """[structs.Head]
size = 4
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
enum = "Yok"
"""
    with pytest.raises(SchemaValueError, match="tanimli degil"):
        load_text(_variant(struct_body=body))


# --------------------------------------------------------------------------- #
# F7-010 — STRUCT ALAN COZUMLEYICI
# --------------------------------------------------------------------------- #


def test_fields_carry_their_offset_and_size() -> None:
    schema = load(EXAMPLE)
    timestamp = schema.struct("FrameHeader").field("timestamp_utc_ns")
    assert timestamp.offset == 8
    assert timestamp.size == 8
    assert timestamp.end == 16
    assert timestamp.unit == "ns"


def test_an_array_field_multiplies_its_size() -> None:
    schema = load(EXAMPLE)
    cit = schema.struct("FrameHeader").field("cit_raw")
    assert cit.count == 16
    assert cit.size == 16
    assert cit.opaque is True


def test_a_field_without_a_name_is_rejected() -> None:
    body = """[structs.Head]
size = 4
[[structs.Head.fields]]
type = "uint32_t"
offset = 0
"""
    with pytest.raises(SchemaValueError, match="name"):
        load_text(_variant(struct_body=body))


def test_a_field_without_a_type_is_rejected() -> None:
    body = """[structs.Head]
size = 4
[[structs.Head.fields]]
name = "a"
offset = 0
"""
    with pytest.raises(SchemaValueError, match="type"):
        load_text(_variant(struct_body=body))


def test_a_field_without_an_offset_is_rejected() -> None:
    """Offset hesaplatılmaz, yazılır; yazılmadıysa şema eksiktir."""
    body = """[structs.Head]
size = 4
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
"""
    with pytest.raises(SchemaValueError, match="offset"):
        load_text(_variant(struct_body=body))


def test_an_unknown_field_type_is_rejected_naming_the_field() -> None:
    body = """[structs.Head]
size = 4
[[structs.Head.fields]]
name = "frame_index"
type = "widget_t"
offset = 0
"""
    with pytest.raises(SchemaTypeError, match="frame_index"):
        load_text(_variant(struct_body=body))


def test_a_negative_offset_is_rejected() -> None:
    body = """[structs.Head]
size = 4
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = -4
"""
    with pytest.raises(SchemaLayoutError, match="negatif"):
        load_text(_variant(struct_body=body))


def test_a_zero_count_is_rejected() -> None:
    body = """[structs.Head]
size = 4
[[structs.Head.fields]]
name = "a"
type = "uint8_t"
offset = 0
count = 0
"""
    with pytest.raises(SchemaLayoutError, match="eleman sayisi"):
        load_text(_variant(struct_body=body))


def test_a_duplicate_field_name_is_rejected() -> None:
    body = """[structs.Head]
size = 8
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 4
"""
    with pytest.raises(SchemaValueError, match="birden fazla"):
        load_text(_variant(struct_body=body))


def test_a_struct_with_no_fields_is_rejected() -> None:
    body = """[structs.Head]
size = 8
"""
    with pytest.raises(SchemaValueError, match="fields"):
        load_text(_variant(struct_body=body))


def test_padding_fields_are_recognised_by_their_name() -> None:
    schema = load(EXAMPLE)
    pad = schema.struct("FrameHeader").field("_pad0")
    assert pad.is_padding is True
    assert schema.struct("FrameHeader").field("frame_index").is_padding is False


def test_an_unknown_field_name_raises_a_key_error() -> None:
    schema = load(EXAMPLE)
    with pytest.raises(KeyError, match="yok"):
        schema.struct("FrameHeader").field("hicyok")


def test_an_unknown_struct_name_lists_what_exists() -> None:
    schema = load(EXAMPLE)
    with pytest.raises(KeyError, match="FrameHeader"):
        schema.struct("Hayalet")


# --------------------------------------------------------------------------- #
# F7-011 — OFFSET CAKISMASI VE BOSLUK
# --------------------------------------------------------------------------- #


def test_overlapping_fields_are_rejected() -> None:
    """Asıl kabul: örtüşen iki alan birinin ötekini bozması demektir."""
    body = """[structs.Head]
size = 8
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 2
"""
    with pytest.raises(SchemaLayoutError, match="ortusuyor"):
        load_text(_variant(struct_body=body))


def test_the_overlap_error_names_both_offsets() -> None:
    """Hangi iki offsetin çakıştığı yazılmazsa, elle aranması gerekir."""
    body = """[structs.Head]
size = 8
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 2
"""
    with pytest.raises(SchemaLayoutError) as caught:
        load_text(_variant(struct_body=body))
    message = str(caught.value)
    assert "Head.b" in message
    assert "2" in message and "4" in message


def test_an_undeclared_gap_is_a_warning_not_an_error() -> None:
    """Bilinçli olabilir; hata saymak doğru şemaları reddederdi."""
    body = """[structs.Head]
size = 12
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 8
[[structs.Head.fields]]
name = "c"
type = "uint32_t"
offset = 4
"""
    schema = load_text(_variant(struct_body=body))
    assert schema.warnings == ()


def test_a_real_gap_produces_a_warning_that_names_its_span() -> None:
    body = """[structs.Head]
size = 12
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 8
[[structs.Head.fields]]
name = "tail"
type = "uint32_t"
offset = 12
"""
    # Bildirilen boyut alanlari kapsamali; tail 16'da biter.
    body = body.replace("size = 12", "size = 16")
    schema = load_text(_variant(struct_body=body))
    assert len(schema.warnings) == 1
    warning = schema.warnings[0]
    assert "4..8" in warning
    assert "4 bayt bosluk" in warning
    assert "b" in warning


def test_fields_may_be_declared_out_of_order() -> None:
    """Sıralama offsetten türer; TOML'daki yazım sırası bağlayıcı değildir."""
    body = """[structs.Head]
size = 8
[[structs.Head.fields]]
name = "second"
type = "uint32_t"
offset = 4
[[structs.Head.fields]]
name = "first"
type = "uint32_t"
offset = 0
"""
    schema = load_text(_variant(struct_body=body))
    assert schema.struct("Head").struct_format("little") == "<II"


# --------------------------------------------------------------------------- #
# F7-012 — BILDIRILEN BOYUT UYUSMAZLIGI
# --------------------------------------------------------------------------- #


def test_a_declared_size_larger_than_the_fields_is_rejected() -> None:
    """Asıl kabul: `size = 16` diyen ama 8 bayt tutan şema reddedilmeli."""
    body = """[structs.Head]
size = 16
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 4
"""
    with pytest.raises(SchemaLayoutError, match="bildirilen boyut 16"):
        load_text(_variant(struct_body=body))


def test_a_field_running_past_the_declared_size_is_rejected() -> None:
    body = """[structs.Head]
size = 6
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 4
"""
    with pytest.raises(SchemaLayoutError, match="disina tasiyor"):
        load_text(_variant(struct_body=body))


def test_a_zero_size_struct_is_rejected() -> None:
    body = """[structs.Head]
size = 0
[[structs.Head.fields]]
name = "a"
type = "uint32_t"
offset = 0
"""
    with pytest.raises(SchemaValueError, match="pozitif"):
        load_text(_variant(struct_body=body))


def test_the_measured_size_is_exposed() -> None:
    schema = load(EXAMPLE)
    definition = schema.struct("FrameHeader")
    assert definition.measured_size == definition.size == 128


# --------------------------------------------------------------------------- #
# F7-013 — HIZALAMA IHLALI
# --------------------------------------------------------------------------- #


def test_a_misaligned_field_is_rejected_in_natural_packing() -> None:
    """Asıl kabul: `natural` kipte 4 baytlık alan 2'ye hizalı olamaz."""
    body = """[structs.Head]
size = 8
[[structs.Head.fields]]
name = "a"
type = "uint16_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 2
"""
    text = _variant(struct_body=body).replace('packing = "packed"', 'packing = "natural"')
    with pytest.raises(SchemaLayoutError, match="hizalamasina uymuyor"):
        load_text(text)


def test_the_alignment_error_suggests_the_packed_mode() -> None:
    """Bilinçli bir paketleme reddedilirse, çıkış yolu gösterilmeli."""
    body = """[structs.Head]
size = 8
[[structs.Head.fields]]
name = "a"
type = "uint16_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 2
"""
    text = _variant(struct_body=body).replace('packing = "packed"', 'packing = "natural"')
    with pytest.raises(SchemaLayoutError) as caught:
        load_text(text)
    assert "packing='packed'" in str(caught.value)


def test_the_same_layout_passes_in_packed_mode() -> None:
    """Karşı yön: `packed` kipte hizalama denetimi yapılmaz."""
    body = """[structs.Head]
size = 6
[[structs.Head.fields]]
name = "a"
type = "uint16_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint32_t"
offset = 2
"""
    schema = load_text(_variant(struct_body=body))
    assert schema.struct("Head").size == 6


def test_single_byte_fields_are_never_misaligned() -> None:
    body = """[structs.Head]
size = 3
[[structs.Head.fields]]
name = "a"
type = "uint8_t"
offset = 0
[[structs.Head.fields]]
name = "b"
type = "uint8_t"
offset = 1
[[structs.Head.fields]]
name = "c"
type = "uint8_t"
offset = 2
"""
    text = _variant(struct_body=body).replace('packing = "packed"', 'packing = "natural"')
    assert load_text(text).struct("Head").size == 3


# --------------------------------------------------------------------------- #
# BIT ALANLARI
# --------------------------------------------------------------------------- #


def test_bit_fields_extract_their_value() -> None:
    schema = load(EXAMPLE)
    status = schema.struct("FrameHeader").field("status")
    gain = next(b for b in status.bits if b.name == "gain_index")
    assert gain.extract(0x00A0) == 0x0A
    assert gain.width == 4


def test_a_single_bit_mask_has_width_one() -> None:
    schema = load(EXAMPLE)
    status = schema.struct("FrameHeader").field("status")
    tx = next(b for b in status.bits if b.name == "tx_active")
    assert tx.width == 1
    assert tx.extract(0x0001) == 1
    assert tx.extract(0x0002) == 0


def test_overlapping_bit_masks_are_rejected() -> None:
    body = """[structs.Head]
size = 2
[[structs.Head.fields]]
name = "status"
type = "uint16_t"
offset = 0
[[structs.Head.fields.bits]]
name = "a"
mask = 0x0003
[[structs.Head.fields.bits]]
name = "b"
mask = 0x0002
"""
    with pytest.raises(SchemaValueError, match="ortusuyor"):
        load_text(_variant(struct_body=body))


def test_a_mask_too_wide_for_its_container_is_rejected() -> None:
    body = """[structs.Head]
size = 1
[[structs.Head.fields]]
name = "status"
type = "uint8_t"
offset = 0
[[structs.Head.fields.bits]]
name = "a"
mask = 0x0100
"""
    with pytest.raises(SchemaValueError, match="sigmiyor"):
        load_text(_variant(struct_body=body))


# --------------------------------------------------------------------------- #
# PAYLOAD
# --------------------------------------------------------------------------- #


def test_the_payload_frame_size_matches_the_budget() -> None:
    """Bayt bütçesindeki 209.920 sayısı buradan türüyor."""
    assert load(EXAMPLE).payload.frame_bytes == 209_920


def test_an_unknown_layout_is_rejected() -> None:
    """Yanlış yerleşim boyut denetimini düşürmez, sensörleri karıştırır."""
    with pytest.raises(SchemaValueError, match="layout"):
        load_text(MINIMAL.replace('layout = "sensor_major"', 'layout = "random"'))


def test_the_sensor_major_flag_follows_the_layout() -> None:
    assert load(EXAMPLE).payload.sensor_major is True
    other = load_text(MINIMAL.replace('layout = "sensor_major"', 'layout = "sample_major"'))
    assert other.payload.sensor_major is False


@pytest.mark.parametrize("key", ["sensor_count", "frame_samples"])
def test_a_non_positive_payload_dimension_is_rejected(key: str) -> None:
    with pytest.raises(SchemaValueError, match="pozitif"):
        load_text(
            MINIMAL.replace(f"{key} = 32", f"{key} = 0").replace(f"{key} = 820", f"{key} = 0")
        )


def test_an_unknown_sample_type_is_rejected() -> None:
    with pytest.raises(SchemaTypeError):
        load_text(MINIMAL.replace('sample_type = "std::complex<float>"', 'sample_type = "blob"'))
