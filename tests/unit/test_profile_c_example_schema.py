"""Örnek TOML şema dosyası — `F7-006`.

Kabul: **`tomllib` ile ayrıştırılır; `FrameHeader` bütün alanları offset
ve cpp tipiyle doludur.**

Bu şema bir örnektir ve öyle olduğu dosyanın başında yazılıdır. Gerçek
Profil C yerleşimi C++ tarafından gelecektir (`E-11`). Örneğin işi,
şema biçimindeki her özelliği çalışır hâlde göstermektir: enum, bit
alanı, dizi, bildirilmiş dolgu ve opak blok.

Testlerin asıl işi bir şeyi kanıtlamaktır: **hiçbir alan uydurulmamıştır.**
CIT, transmisyon ve platform verilerinin iç yerleşimi bilinmiyor
(`D-30`, `D-31`); bunlar opak bayt blokları olarak durur. Bir gün
öğrenildiklerinde açılacaklar. Şimdiden alan adı yazmak, o alanların
bilindiği izlenimi verirdi.

Testler ayrıca offsetlerin gerçekten tutarlı olduğunu ölçer: alanlar
örtüşmüyor, bildirilen boyutu tam dolduruyor ve her tip `struct` ile
ölçülebiliyor.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import pytest

from sonar_analyzer.io.schema import load_path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas" / "profile-c.example.toml"

#: cpp tipi -> bayt. `char[N]` ve dizi alanlari `count` ile carpilir.
TYPE_SIZE: dict[str, int] = {
    "uint8_t": 1,
    "int8_t": 1,
    "uint16_t": 2,
    "int16_t": 2,
    "uint32_t": 4,
    "int32_t": 4,
    "uint64_t": 8,
    "int64_t": 8,
    "float": 4,
    "double": 8,
    "char[N]": 1,
}

SENSOR_COUNT = 32
FRAME_SAMPLES = 820


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    assert SCHEMA.is_file(), f"ornek sema yok: {SCHEMA}"
    return load_path(SCHEMA)


@pytest.fixture(scope="module")
def raw() -> str:
    return SCHEMA.read_text(encoding="utf-8")


def _field_span(field: dict[str, Any]) -> tuple[int, int]:
    """Alanın kapladığı (başlangıç, bitiş) aralığı."""
    size = TYPE_SIZE[field["type"]] * int(field.get("count", 1))
    start = int(field["offset"])
    return start, start + size


# --------------------------------------------------------------------------- #
# AYRISTIRILIYOR MU
# --------------------------------------------------------------------------- #


def test_the_schema_parses(schema: dict[str, Any]) -> None:
    """Asıl kabul: dosya bir TOML ayrıştırıcısıyla okunabilmeli."""
    assert set(schema) == {"schema", "enums", "structs", "payload"}


def test_the_schema_declares_its_identity(schema: dict[str, Any]) -> None:
    """Kimlik ve sürüm olmadan şema ile kayıt karşılaştırılamaz."""
    head = schema["schema"]
    assert head["id"] == "sonar-profile-c"
    assert isinstance(head["version"], int)


def test_the_schema_declares_byte_order_and_packing(schema: dict[str, Any]) -> None:
    head = schema["schema"]
    assert head["endianness"] in {"little", "big"}
    assert head["packing"] in {"packed", "natural"}


# --------------------------------------------------------------------------- #
# ENUM'LAR
# --------------------------------------------------------------------------- #


def test_every_enum_declares_its_underlying_type(schema: dict[str, Any]) -> None:
    """Bildirilmezse derleyici seçer ve boyut değişebilir."""
    for name, enum in schema["enums"].items():
        assert "underlying" in enum, f"{name} temel tipini bildirmiyor"
        assert enum["underlying"] in TYPE_SIZE, f"{name} bilinmeyen temel tip"


def test_no_enum_repeats_a_value(schema: dict[str, Any]) -> None:
    """Yinelenen değer, geri eşlemeyi belirsiz kılar."""
    for name, enum in schema["enums"].items():
        values = list(enum["values"].values())
        assert len(values) == len(set(values)), f"{name} yinelenen değer taşıyor"


def test_every_enum_value_fits_its_underlying_type(schema: dict[str, Any]) -> None:
    for name, enum in schema["enums"].items():
        limit = 1 << (8 * TYPE_SIZE[enum["underlying"]])
        for key, value in enum["values"].items():
            assert 0 <= value < limit, f"{name}.{key} temel tipe sığmıyor"


def test_the_unknown_value_is_zero_where_present(schema: dict[str, Any]) -> None:
    """Sıfır öntanımlı bayt değeridir; bilinmeyeni oraya koymak güvenlidir."""
    for name, enum in schema["enums"].items():
        if "UNKNOWN" in enum["values"]:
            assert enum["values"]["UNKNOWN"] == 0, f"{name}.UNKNOWN sıfır değil"


# --------------------------------------------------------------------------- #
# OFFSETLER TUTARLI MI
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("struct_name", ["FileHeader", "FrameHeader"])
def test_every_field_declares_type_and_offset(schema: dict[str, Any], struct_name: str) -> None:
    """Asıl kabul: her alan offset ve cpp tipiyle dolu olmalı."""
    for field in schema["structs"][struct_name]["fields"]:
        assert "name" in field, f"{struct_name}: adsız alan"
        assert "type" in field, f"{struct_name}.{field.get('name')}: tip yok"
        assert "offset" in field, f"{struct_name}.{field.get('name')}: offset yok"
        assert field["type"] in TYPE_SIZE, f"{struct_name}.{field['name']}: bilinmeyen tip"


@pytest.mark.parametrize("struct_name", ["FileHeader", "FrameHeader"])
def test_no_two_fields_overlap(schema: dict[str, Any], struct_name: str) -> None:
    """Örtüşen iki alan, birinin diğerini sessizce bozması demektir."""
    spans = sorted(_field_span(f) for f in schema["structs"][struct_name]["fields"])
    for (_, previous_end), (next_start, _) in zip(spans, spans[1:]):
        assert previous_end <= next_start, f"{struct_name}: {previous_end} > {next_start} örtüşme"


@pytest.mark.parametrize("struct_name", ["FileHeader", "FrameHeader"])
def test_the_fields_fill_the_declared_size_exactly(
    schema: dict[str, Any], struct_name: str
) -> None:
    """Bildirilen boyut alanları kapsamıyorsa, okuma kayar."""
    definition = schema["structs"][struct_name]
    end = max(_field_span(f)[1] for f in definition["fields"])
    assert end == definition["size"], (
        f"{struct_name}: alanlar {end} bayt, bildirilen {definition['size']}"
    )


@pytest.mark.parametrize("struct_name", ["FileHeader", "FrameHeader"])
def test_no_field_starts_before_zero(schema: dict[str, Any], struct_name: str) -> None:
    for field in schema["structs"][struct_name]["fields"]:
        assert int(field["offset"]) >= 0


@pytest.mark.parametrize("struct_name", ["FileHeader", "FrameHeader"])
def test_no_field_name_is_used_twice(schema: dict[str, Any], struct_name: str) -> None:
    names = [f["name"] for f in schema["structs"][struct_name]["fields"]]
    assert len(names) == len(set(names)), f"{struct_name}: yinelenen alan adı"


@pytest.mark.parametrize("struct_name", ["FileHeader", "FrameHeader"])
def test_the_declared_size_is_measurable_with_struct(
    schema: dict[str, Any], struct_name: str
) -> None:
    """Alanlardan üretilen `struct` biçimi, bildirilen boyutu vermeli."""
    codes = {
        "uint8_t": "B",
        "int8_t": "b",
        "uint16_t": "H",
        "int16_t": "h",
        "uint32_t": "I",
        "int32_t": "i",
        "uint64_t": "Q",
        "int64_t": "q",
        "float": "f",
        "double": "d",
    }
    parts = ["<"]
    for field in schema["structs"][struct_name]["fields"]:
        count = int(field.get("count", 1))
        if field["type"] == "char[N]":
            parts.append(f"{count}s")
        else:
            parts.append(f"{count}{codes[field['type']]}" if count > 1 else codes[field["type"]])
    assert struct.calcsize("".join(parts)) == schema["structs"][struct_name]["size"]


# --------------------------------------------------------------------------- #
# BIT ALANLARI
# --------------------------------------------------------------------------- #


def test_the_status_field_carries_bit_definitions(schema: dict[str, Any]) -> None:
    status = next(f for f in schema["structs"]["FrameHeader"]["fields"] if f["name"] == "status")
    assert "bits" in status
    assert len(status["bits"]) >= 3


def test_no_two_bit_masks_overlap(schema: dict[str, Any]) -> None:
    """Örtüşen maskeler bir biti iki anlama gelir kılar."""
    status = next(f for f in schema["structs"]["FrameHeader"]["fields"] if f["name"] == "status")
    combined = 0
    for bit in status["bits"]:
        mask = int(bit["mask"])
        assert combined & mask == 0, f"{bit['name']} maskesi örtüşüyor"
        combined |= mask


def test_every_bit_mask_fits_its_container(schema: dict[str, Any]) -> None:
    status = next(f for f in schema["structs"]["FrameHeader"]["fields"] if f["name"] == "status")
    limit = 1 << (8 * TYPE_SIZE[status["type"]])
    for bit in status["bits"]:
        assert 0 < int(bit["mask"]) < limit, f"{bit['name']} maskesi alana sığmıyor"


def test_a_multi_bit_mask_declares_its_shift(schema: dict[str, Any]) -> None:
    """Kaydırma yazılmazsa çok bitli bir alan yanlış okunur."""
    status = next(f for f in schema["structs"]["FrameHeader"]["fields"] if f["name"] == "status")
    gain = next(b for b in status["bits"] if b["name"] == "gain_index")
    assert gain["shift"] == 4
    assert int(gain["mask"]) >> gain["shift"] == 0x0F


# --------------------------------------------------------------------------- #
# UYDURULMAMIS OLMA — EN ONEMLI BOLUM
# --------------------------------------------------------------------------- #


def test_the_file_announces_that_it_is_an_example(raw: str) -> None:
    """Örnek olduğu yazılmazsa, gerçek yerleşim sanılır."""
    head = raw[:1200]
    assert "ORNEKTIR" in head
    assert "E-11" in head


def test_the_unknown_blocks_are_marked_opaque(schema: dict[str, Any]) -> None:
    """Asıl kabul: bilinmeyen alanlar uydurulmamış, opak bırakılmış olmalı."""
    fields = {f["name"]: f for f in schema["structs"]["FrameHeader"]["fields"]}
    for name in ("cit_raw", "tx_raw", "platform_raw"):
        assert name in fields, f"{name} yok"
        assert fields[name].get("opaque") is True, f"{name} opak işaretlenmemiş"
        assert fields[name]["type"] == "uint8_t", f"{name} bayt bloğu olmalı"


def test_each_opaque_block_cites_its_open_decision(schema: dict[str, Any]) -> None:
    """Hangi sorunun cevabını beklediği yazılmazsa, opaklık kalıcılaşır."""
    fields = {f["name"]: f for f in schema["structs"]["FrameHeader"]["fields"]}
    assert "D-30" in fields["cit_raw"]["note"]
    assert "D-31" in fields["tx_raw"]["note"]
    for name in ("cit_raw", "tx_raw", "platform_raw"):
        assert "BILINMIYOR" in fields[name]["note"]


def test_no_invented_field_names_for_the_unknown_blocks(raw: str) -> None:
    """`cit_period`, `tx_power` gibi bir ad, o alanın bilindiği izlenimi verirdi."""
    for invented in ("cit_period", "cit_length", "tx_power", "tx_frequency", "platform_speed"):
        assert invented not in raw, f"uydurulmus alan adi: {invented}"


def test_the_padding_fields_are_annotated(schema: dict[str, Any]) -> None:
    """Dolgu bildirilirse boyut kendi kendini doğrular."""
    for struct_name in ("FileHeader", "FrameHeader"):
        pads = [f for f in schema["structs"][struct_name]["fields"] if f["name"].startswith("_")]
        assert pads, f"{struct_name}: bildirilmiş dolgu yok"
        for pad in pads:
            assert "note" in pad, f"{struct_name}.{pad['name']}: gerekçe yazılmamış"


# --------------------------------------------------------------------------- #
# PAYLOAD
# --------------------------------------------------------------------------- #


def test_the_payload_matches_the_profile_constants(schema: dict[str, Any]) -> None:
    payload = schema["payload"]
    assert payload["sensor_count"] == SENSOR_COUNT
    assert payload["frame_samples"] == FRAME_SAMPLES
    assert payload["sample_type"] == "std::complex<float>"


def test_the_payload_layout_is_explicit(schema: dict[str, Any]) -> None:
    """Yanlış yerleşim boyut denetimini düşürmez, sensörleri karıştırır."""
    assert schema["payload"]["layout"] in {"sensor_major", "sample_major"}


def test_the_payload_size_matches_the_byte_budget(schema: dict[str, Any]) -> None:
    """Örnek şema, belgedeki bayt bütçesini doğrulamalı."""
    payload = schema["payload"]
    frame_bytes = payload["sensor_count"] * payload["frame_samples"] * 8
    assert frame_bytes == 209_920


def test_the_canonical_time_field_is_marked(schema: dict[str, Any]) -> None:
    """Kanonik zaman kaynağı şemada da görünmeli (`D-33`)."""
    timestamp = next(
        f for f in schema["structs"]["FrameHeader"]["fields"] if f["name"] == "timestamp_utc_ns"
    )
    assert timestamp["type"] == "int64_t"
    assert timestamp["unit"] == "ns"
    assert "KANONIK" in timestamp["description"]


def test_both_crc_fields_say_they_exclude_themselves(schema: dict[str, Any]) -> None:
    """`ADR-011`: CRC kendi alanı hariç hesaplanır."""
    for struct_name in ("FileHeader", "FrameHeader"):
        crc = next(
            f for f in schema["structs"][struct_name]["fields"] if f["name"] == "header_crc32"
        )
        assert "haric" in crc["description"]
        assert "ADR-011" in crc["description"]
