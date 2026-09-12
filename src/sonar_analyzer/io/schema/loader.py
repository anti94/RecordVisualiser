"""TOML şema yükleyicisi — `F7-008`…`F7-013`.

Yükleme tek geçişte yapılır ve **doğrulanmış** bir `Schema` döndürür.
Doğrulamayı okuma anına ertelemek, bir yazım hatasının ancak o alan ilk
kez okunduğunda ortaya çıkması demektir — yani saatler sonra, yanlış
sayılara bakarken.

Hatalar erken ve **adres vererek** verilir: hangi struct, hangi alan,
hangi offset ve ne beklendiği. "Şema geçersiz" diyen bir mesaj, yüz
alanlı bir dosyayı baştan sona okutur.

Hata ile uyarı ayrılır. Bildirilmemiş bir boşluk uyarıdır: bilinçli
olabilir. Bildirilen boyutun alanları kapsamaması hatadır: hiçbir
durumda doğru olamaz.

TOML ayrıştırıcısı `Any` döndürür. Ham `Any` değerleri doğrudan
kullanmak yerine her biri `_as_*` yardımcılarından geçirilir: hem tip
denetimi tek yerde toplanır hem de hata mesajı hangi anahtarın yanlış
olduğunu söyler. `Any`'yi olduğu gibi taşımak, katı tip denetiminde
sessizce bilinmeyen tiplere yol açardı.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sonar_analyzer.io.schema._toml import load_path, loads
from sonar_analyzer.io.schema.errors import SchemaLayoutError, SchemaValueError
from sonar_analyzer.io.schema.model import (
    BitField,
    EnumDef,
    FieldDef,
    PayloadDef,
    Schema,
    StructDef,
)
from sonar_analyzer.io.schema.types import resolve

VALID_ENDIANNESS = ("little", "big")
VALID_PACKING = ("packed", "natural")
VALID_LAYOUT = ("sensor_major", "sample_major")

Table = dict[str, Any]


# --------------------------------------------------------------------------- #
# TIP DARALTMA
# --------------------------------------------------------------------------- #


def _require(mapping: Table, key: str, where: str) -> Any:
    if key not in mapping:
        raise SchemaValueError(f"{where}: zorunlu alan eksik: {key!r}")
    return mapping[key]


def _as_int(value: Any, *, where: str, key: str) -> int:
    """Tamsayı daraltması.

    `bool` ayrıca elenir: Python'da `True` bir `int`'tir ve
    `isinstance(True, int)` doğrudur. `version = true` yazan bir şema
    sessizce sürüm 1 sayılırdı.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValueError(f"{where}: {key!r} tamsayi olmali, verilen {value!r}")
    return value


def _as_str(value: Any, *, where: str, key: str) -> str:
    if not isinstance(value, str):
        raise SchemaValueError(f"{where}: {key!r} metin olmali, verilen {value!r}")
    return value


def _as_table(value: Any, *, where: str, allow_empty: bool = True) -> Table:
    if not isinstance(value, dict):
        raise SchemaValueError(f"{where}: bir tablo olmali, verilen {type(value).__name__}")
    table = cast("Table", value)
    if not allow_empty and not table:
        raise SchemaValueError(f"{where}: bos olmayan bir tablo olmali")
    return table


def _as_list(value: Any, *, where: str, allow_empty: bool = True) -> list[Any]:
    if not isinstance(value, list):
        raise SchemaValueError(f"{where}: bir liste olmali, verilen {type(value).__name__}")
    items = cast("list[Any]", value)
    if not allow_empty and not items:
        raise SchemaValueError(f"{where}: bos olmayan bir liste olmali")
    return items


def _text(mapping: Table, key: str) -> str:
    """İsteğe bağlı metin alanı; yoksa boş dizge."""
    value = mapping.get(key, "")
    return value if isinstance(value, str) else str(value)


def _choice(mapping: Table, key: str, allowed: tuple[str, ...], default: str, where: str) -> str:
    """Kapalı bir değer kümesinden seçim; anahtar yoksa öntanım.

    Anahtarın **yokluğu** ile **boş yazılmış olması** ayrılır. `endianness`
    hiç yazılmamışsa öntanım makul bir varsayımdır. Ama `endianness = ""`
    yazılmışsa bu bir yazım hatasıdır ve sessizce öntanıma düşmek onu
    gizlerdi: kullanıcı bir şey yazdığını sanır, başka bir şey uygulanır.
    """
    if key not in mapping:
        return default
    value = _as_str(mapping[key], where=where, key=key)
    if value not in allowed:
        raise SchemaValueError(f"{where}.{key} {allowed} icinden biri olmali, verilen {value!r}")
    return value


# --------------------------------------------------------------------------- #
# ENUM
# --------------------------------------------------------------------------- #


def _build_enum(name: str, raw: Table) -> EnumDef:
    where = f"enums.{name}"
    underlying = resolve(_as_str(_require(raw, "underlying", where), where=where, key="underlying"))
    values_raw = _as_table(
        _require(raw, "values", where), where=f"{where}.values", allow_empty=False
    )

    values: dict[str, int] = {}
    seen: dict[int, str] = {}
    limit = 1 << (8 * underlying.size)
    for key, value in values_raw.items():
        number = _as_int(value, where=where, key=key)
        if not 0 <= number < limit:
            raise SchemaValueError(
                f"{where}.{key}: {number} degeri temel tip {underlying.cpp} "
                f"araligina (0..{limit - 1}) sigmiyor"
            )
        if number in seen:
            raise SchemaValueError(
                f"{where}: {key!r} ve {seen[number]!r} ayni degeri ({number}) tasiyor; "
                f"deger->isim eslemesi belirsiz kalir"
            )
        seen[number] = key
        values[key] = number

    return EnumDef(
        name=name, underlying=underlying, values=values, description=_text(raw, "description")
    )


# --------------------------------------------------------------------------- #
# ALAN VE BIT ALANI
# --------------------------------------------------------------------------- #


def _build_bits(
    field_name: str, raw_bits: Any, container_size: int, where: str
) -> tuple[BitField, ...]:
    entries = _as_list(raw_bits, where=f"{where}.bits")
    limit = 1 << (8 * container_size)
    bits: list[BitField] = []
    combined = 0

    for item in entries:
        entry = _as_table(item, where=f"{where}.bits")
        name = _as_str(_require(entry, "name", where), where=where, key="name")
        mask = _as_int(_require(entry, "mask", where), where=where, key="mask")
        shift = _as_int(entry.get("shift", 0), where=where, key="shift")
        if not 0 < mask < limit:
            raise SchemaValueError(
                f"{where}.{name}: 0x{mask:X} maskesi {field_name} alanina "
                f"({container_size} bayt) sigmiyor"
            )
        if combined & mask:
            raise SchemaValueError(
                f"{where}.{name}: 0x{mask:X} maskesi daha once tanimlanmis bir bitle "
                f"ortusuyor; bir bit iki anlama gelemez"
            )
        combined |= mask
        bits.append(
            BitField(name=name, mask=mask, shift=shift, description=_text(entry, "description"))
        )
    return tuple(bits)


def _build_field(struct_name: str, raw: Table) -> FieldDef:
    where = f"structs.{struct_name}"
    name = _as_str(_require(raw, "name", where), where=where, key="name")
    where = f"{where}.{name}"

    cpp_type = resolve(_as_str(_require(raw, "type", where), where=where, key="type"), field=name)
    offset = _as_int(_require(raw, "offset", where), where=where, key="offset")
    if offset < 0:
        raise SchemaLayoutError(
            f"offset negatif olamaz: {offset}", struct_name=struct_name, field=name
        )
    count = _as_int(raw.get("count", 1), where=where, key="count")
    if count < 1:
        raise SchemaLayoutError(
            f"eleman sayisi >= 1 olmali, verilen {count}", struct_name=struct_name, field=name
        )

    bits: tuple[BitField, ...] = ()
    if "bits" in raw:
        bits = _build_bits(name, raw["bits"], cpp_type.size * count, where)

    return FieldDef(
        name=name,
        cpp_type=cpp_type,
        offset=offset,
        count=count,
        enum=_text(raw, "enum"),
        unit=_text(raw, "unit"),
        description=_text(raw, "description"),
        note=_text(raw, "note"),
        opaque=bool(raw.get("opaque", False)),
        bits=bits,
    )


# --------------------------------------------------------------------------- #
# STRUCT VE YERLESIM DENETIMI
# --------------------------------------------------------------------------- #


def _check_layout(definition: StructDef, *, packed: bool) -> list[str]:
    """Offset, örtüşme, boyut ve hizalama denetimleri.

    Döndürülen liste **uyarılardır**; hatalar istisna olarak atılır.
    """
    name = definition.name
    ordered = sorted(definition.fields, key=lambda f: f.offset)

    for field in ordered:
        if field.end > definition.size:
            raise SchemaLayoutError(
                f"alan {field.offset}..{field.end} araliginda ama struct "
                f"{definition.size} bayt; alan struct'in disina tasiyor",
                struct_name=name,
                field=field.name,
            )
        if not packed and field.cpp_type.size > 1 and field.offset % field.cpp_type.size:
            raise SchemaLayoutError(
                f"offset {field.offset}, {field.cpp_type.cpp} tipinin "
                f"{field.cpp_type.size} bayt hizalamasina uymuyor "
                f"(packing='natural'; bilincliyse packing='packed' yazin)",
                struct_name=name,
                field=field.name,
            )

    warnings: list[str] = []
    cursor = 0
    for field in ordered:
        if field.offset < cursor:
            raise SchemaLayoutError(
                f"offset {field.offset}, onceki alanin bittigi {cursor} offsetinden "
                f"once; alanlar ortusuyor",
                struct_name=name,
                field=field.name,
            )
        if field.offset > cursor:
            warnings.append(
                f"{name}: {cursor}..{field.offset} arasinda bildirilmemis "
                f"{field.offset - cursor} bayt bosluk ({field.name} alanindan once)"
            )
        cursor = field.end

    if cursor != definition.size:
        raise SchemaLayoutError(
            f"alanlar {cursor} bayt kapliyor ama bildirilen boyut {definition.size}",
            struct_name=name,
        )
    return warnings


def _build_struct(name: str, raw: Table, *, packed: bool) -> tuple[StructDef, list[str]]:
    where = f"structs.{name}"
    size = _as_int(_require(raw, "size", where), where=where, key="size")
    if size < 1:
        raise SchemaValueError(f"{where}: 'size' pozitif olmali, verilen {size}")

    raw_fields = _as_list(
        _require(raw, "fields", where), where=f"{where}.fields", allow_empty=False
    )
    fields = tuple(_build_field(name, _as_table(item, where=where)) for item in raw_fields)

    names = [f.name for f in fields]
    duplicate = next((n for n in names if names.count(n) > 1), None)
    if duplicate is not None:
        raise SchemaValueError(f"{where}: {duplicate!r} alan adi birden fazla kez tanimli")

    definition = StructDef(
        name=name, size=size, fields=fields, description=_text(raw, "description")
    )
    return definition, _check_layout(definition, packed=packed)


# --------------------------------------------------------------------------- #
# PAYLOAD
# --------------------------------------------------------------------------- #


def _build_payload(raw: Any) -> PayloadDef:
    where = "payload"
    table = _as_table(raw, where=where)
    sensor_count = _as_int(_require(table, "sensor_count", where), where=where, key="sensor_count")
    frame_samples = _as_int(
        _require(table, "frame_samples", where), where=where, key="frame_samples"
    )
    if sensor_count < 1 or frame_samples < 1:
        raise SchemaValueError(f"{where}: sensor_count ve frame_samples pozitif olmali")

    sample_type = resolve(
        _as_str(_require(table, "sample_type", where), where=where, key="sample_type")
    )
    layout = _choice(table, "layout", VALID_LAYOUT, "sensor_major", where)
    return PayloadDef(
        sensor_count=sensor_count,
        frame_samples=frame_samples,
        sample_type=sample_type,
        layout=layout,
        description=_text(table, "description"),
    )


# --------------------------------------------------------------------------- #
# SEMA
# --------------------------------------------------------------------------- #


def build(raw: Table) -> Schema:
    """Ham TOML sözlüğünden doğrulanmış bir şema kurar."""
    head = _as_table(_require(raw, "schema", "sema"), where="schema")

    schema_id = _as_str(_require(head, "id", "schema"), where="schema", key="id")
    version = _as_int(_require(head, "version", "schema"), where="schema", key="version")
    endianness = _choice(head, "endianness", VALID_ENDIANNESS, "little", "schema")
    packing = _choice(head, "packing", VALID_PACKING, "packed", "schema")

    raw_enums = _as_table(raw.get("enums", {}), where="enums")
    enums = {
        name: _build_enum(name, _as_table(value, where=f"enums.{name}"))
        for name, value in raw_enums.items()
    }

    raw_structs = _as_table(_require(raw, "structs", "sema"), where="structs", allow_empty=False)
    packed = packing == "packed"
    structs: dict[str, StructDef] = {}
    warnings: list[str] = []
    for name, value in raw_structs.items():
        definition, struct_warnings = _build_struct(
            name, _as_table(value, where=f"structs.{name}"), packed=packed
        )
        structs[name] = definition
        warnings.extend(struct_warnings)

    for definition in structs.values():
        for field in definition.fields:
            if field.enum and field.enum not in enums:
                raise SchemaValueError(
                    f"structs.{definition.name}.{field.name}: {field.enum!r} adli enum "
                    f"tanimli degil; tanimli olanlar: {sorted(enums)}"
                )

    return Schema(
        id=schema_id,
        version=version,
        endianness=endianness,
        packing=packing,
        enums=enums,
        structs=structs,
        payload=_build_payload(_require(raw, "payload", "sema")),
        description=_text(head, "description"),
        warnings=tuple(warnings),
    )


def load_text(text: str) -> Schema:
    """TOML metninden şema kurar."""
    return build(loads(text))


def load(path: Path) -> Schema:
    """TOML dosyasından şema kurar."""
    return build(load_path(path))
